"""Comprobaciones de configuración al arrancar: impide ejecutar fuera de desarrollo con secretos por defecto o demasiado cortos.
Copiar a api/app/security.py antes de aplicar parche_b_seguridad.py."""
from __future__ import annotations

MIN_SECRET = 32
DEFAULT_SECRETS = {"cambiar", "cambiar-en-produccion", "changeme", "secret"}


def _bad(v: str | None) -> bool:
    return not v or len(v) < MIN_SECRET or v in DEFAULT_SECRETS


def check_config(env: dict, dev: bool) -> tuple[list[str], list[str]]:
    """Devuelve (errores, avisos). Fuera de desarrollo, los errores impiden arrancar."""
    errors, warnings = [], []
    if dev:
        warnings.append("MATHEVAL_DEV=1: acepta usuarios por cabecera y ejercicios sin revisar; usar solo en desarrollo")
        return errors, warnings
    if _bad(env.get("PSEUDONYM_SECRET")):
        errors.append(f"PSEUDONYM_SECRET falta, es el valor por defecto o tiene menos de {MIN_SECRET} caracteres")
    if env.get("LTI_HANDOFF_SECRET") or env.get("SESSION_SECRET"):
        for name in ("LTI_HANDOFF_SECRET", "SESSION_SECRET"):
            if _bad(env.get(name)):
                errors.append(f"{name} falta, es el valor por defecto o tiene menos de {MIN_SECRET} caracteres")
    if not env.get("OIDC_ISSUER") and not env.get("SESSION_SECRET"):
        errors.append("No hay forma de autenticar usuarios: definí OIDC_ISSUER (Keycloak) o el acceso por LTI (SESSION_SECRET)")
    origin = env.get("WEB_ORIGIN", "http://localhost:3000")
    if origin.startswith("http://") and "localhost" not in origin:
        warnings.append("WEB_ORIGIN usa http sin cifrado")
    if env.get("REQUIRE_CONSENT") == "0":
        warnings.append("REQUIRE_CONSENT=0: los estudiantes pueden practicar sin que la escuela confirme el consentimiento")
    return errors, warnings
