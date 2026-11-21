"""Validación de configuración sensible antes de arrancar servicios fuera de desarrollo."""
from __future__ import annotations

MIN_SECRET = 32
_DEFAULTS = {"cambiar", "cambiar-en-produccion", "changeme", "secret", "password"}


def _weak(value: str | None) -> bool:
    if not value:
        return True
    normalized = value.strip().lower()
    return (len(normalized) < MIN_SECRET or normalized in _DEFAULTS
            or normalized.startswith(("dev-", "test-", "example-", "sample-"))
            or "cambiar" in normalized or "changeme" in normalized)


def _local_http(value: str) -> bool:
    return value.startswith(("http://localhost", "http://127.0.0.1", "http://[::1]"))


def check_config(env: dict, dev: bool) -> tuple[list[str], list[str]]:
    """Devuelve errores que bloquean producción y avisos de configuración."""
    errors: list[str] = []
    warnings: list[str] = []
    if dev:
        warnings.append("MATHEVAL_DEV=1: autenticación por cabecera y contenido sin revisión; solo para desarrollo local")
        return errors, warnings

    if _weak(env.get("PSEUDONYM_SECRET")):
        errors.append(f"PSEUDONYM_SECRET debe tener al menos {MIN_SECRET} caracteres aleatorios")

    lti_enabled = bool(env.get("LTI_HANDOFF_SECRET") or env.get("LTI_SECRET_KEY"))
    if lti_enabled:
        for key in ("LTI_HANDOFF_SECRET", "SESSION_SECRET", "LTI_SECRET_KEY"):
            if _weak(env.get(key)):
                errors.append(f"{key} falta o es demasiado débil (mínimo {MIN_SECRET} caracteres)")
        lti_web = env.get("WEB_URL", "")
        if not lti_web:
            errors.append("WEB_URL es obligatorio cuando LTI está habilitado")
        elif lti_web.startswith("http://") and not _local_http(lti_web):
            errors.append("WEB_URL debe usar HTTPS fuera de localhost")
    if not env.get("OIDC_ISSUER") and not lti_enabled:
        errors.append("No hay autenticación configurada: definí OIDC_ISSUER o la configuración completa de LTI")

    issuer = env.get("OIDC_ISSUER", "")
    if issuer and issuer.startswith("http://") and not _local_http(issuer):
        errors.append("OIDC_ISSUER debe usar HTTPS fuera de localhost")
    origin = env.get("WEB_ORIGIN", "")
    if not origin:
        errors.append("WEB_ORIGIN es obligatorio en producción")
    elif origin.startswith("http://") and not _local_http(origin):
        errors.append("WEB_ORIGIN debe usar HTTPS fuera de localhost")
    database_url = env.get("DATABASE_URL", "")
    if not database_url.startswith(("postgresql://", "postgres://")):
        errors.append("DATABASE_URL debe apuntar a PostgreSQL en producción")
    if env.get("REQUIRE_CONSENT") == "0":
        warnings.append("REQUIRE_CONSENT=0: la práctica no exige constancia de consentimiento institucional")
    return errors, warnings
