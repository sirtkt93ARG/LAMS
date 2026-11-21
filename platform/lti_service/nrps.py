"""Cliente mínimo y de solo lectura para LTI Names and Role Provisioning Services (NRPS)."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

from .ags import get_access_token

SCOPE_NRPS = "https://purl.imsglobal.org/spec/lti-nrps/scope/contextmembership.readonly"
ACCEPT_NRPS = "application/vnd.ims.lti-nrps.v2.membershipcontainer+json"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """No reenvía el bearer token a otro destino mediante redirecciones HTTP."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _allowed_url(url: str, issuer: str, allowed_hosts: list[str] | None, dev: bool) -> str:
    parsed = urllib.parse.urlsplit(url)
    if not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("URL NRPS inválida")
    configured = {str(h).strip().lower().rstrip(".") for h in (allowed_hosts or []) if str(h).strip()}
    if not configured:
        issuer_host = urllib.parse.urlsplit(issuer).hostname
        configured = {issuer_host.lower().rstrip(".")} if issuer_host else set()
    if parsed.scheme != "https":
        if not (dev and parsed.scheme == "http" and parsed.hostname.lower().rstrip(".") in configured):
            raise ValueError("NRPS requiere HTTPS fuera de desarrollo y hosts permitidos")
    if parsed.hostname.lower().rstrip(".") not in configured:
        raise ValueError("el host NRPS no está autorizado para este registro LTI")
    return url


def _next_link(header: str | None) -> str | None:
    if not header:
        return None
    match = re.search(r'<([^>]+)>\s*;\s*rel=["\']?next["\']?', header, re.IGNORECASE)
    return match.group(1) if match else None


def fetch_memberships(context_memberships_url: str, token: str, *, issuer: str,
                      allowed_hosts: list[str] | None = None, dev: bool = False,
                      timeout: float = 10, max_pages: int = 10, max_members: int = 5000) -> list[dict]:
    """Obtiene solo user_id y nombre visible de estudiantes; nunca devuelve emails ni roles."""
    opener = urllib.request.build_opener(_NoRedirect)
    current = _allowed_url(context_memberships_url, issuer, allowed_hosts, dev)
    seen: set[str] = set()
    members: list[dict] = []
    for page in range(max_pages):
        current = _allowed_url(current, issuer, allowed_hosts, dev)
        req = urllib.request.Request(current, headers={
            "Authorization": f"Bearer {token}",
            "Accept": ACCEPT_NRPS,
        })
        with opener.open(req, timeout=timeout) as response:
            raw = response.read(5 * 1024 * 1024 + 1)
            if len(raw) > 5 * 1024 * 1024:
                raise ValueError("respuesta NRPS supera el tamaño permitido")
            payload = json.loads(raw)
            link = response.headers.get("Link")
        if not isinstance(payload, dict):
            raise ValueError("respuesta NRPS inválida")
        entries = payload.get("members", [])
        if not isinstance(entries, list):
            raise ValueError("respuesta NRPS sin lista de miembros")
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            user_id = entry.get("user_id")
            roles = entry.get("roles", [])
            if not isinstance(user_id, str) or not user_id or len(user_id) > 512 or user_id in seen:
                continue
            if not isinstance(roles, list) or not any(str(role).endswith("#Learner") for role in roles):
                continue
            status = entry.get("status")
            if status is not None and str(status).lower() != "active":
                continue
            name = entry.get("name")
            if not isinstance(name, str) or not name.strip():
                parts = [entry.get("given_name"), entry.get("family_name")]
                name = " ".join(p.strip() for p in parts if isinstance(p, str) and p.strip())
            seen.add(user_id)
            members.append({"user_id": user_id, "name": name.strip()[:200] if isinstance(name, str) else ""})
            if len(members) > max_members:
                raise ValueError("el roster NRPS supera el límite de miembros permitido")
        next_url = _next_link(link)
        if not next_url:
            return members
        if page + 1 >= max_pages:
            raise ValueError("el roster NRPS supera el límite de páginas permitido")
        current = urllib.parse.urljoin(current, next_url)
    return members


def fetch_roster(context_memberships_url: str, issuer: str, client_id: str, token_url: str,
                 private_pem: bytes, kid: str, *, allowed_hosts: list[str] | None = None,
                 dev: bool = False, timeout: float = 10) -> list[dict]:
    """Solicita el scope NRPS al LMS y descarga el roster validando cada URL de paginación."""
    _allowed_url(context_memberships_url, issuer, allowed_hosts, dev)
    token = get_access_token(token_url, client_id, private_pem, kid, scope=SCOPE_NRPS, timeout=timeout)
    return fetch_memberships(context_memberships_url, token, issuer=issuer,
                             allowed_hosts=allowed_hosts, dev=dev, timeout=timeout)
