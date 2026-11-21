"""Crea el par de claves RSA de la herramienta LTI y la configuración para el LMS simulado."""
import json, os, pathlib, sys
from urllib.parse import urlparse
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

cfg = pathlib.Path(os.getenv("LTI_CONFIG_DIR", "lti_service/configs"))
cfg.mkdir(parents=True, exist_ok=True)
output_name = os.getenv("LTI_CONFIG_OUTPUT", "lti.mock.json")
if (cfg / output_name).exists() and "--force" not in sys.argv:
    print(f"Ya existe {cfg / output_name} (usá --force para regenerar)."); sys.exit(0)
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
(cfg / "private.key").write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
                                                    serialization.NoEncryption()))
(cfg / "public.key").write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM,
                                                               serialization.PublicFormat.SubjectPublicKeyInfo))
os.chmod(cfg / "private.key", 0o600)
os.chmod(cfg / "public.key", 0o644)
issuer = os.getenv("MOCK_ISS", "http://localhost:8300").rstrip("/")
default_nrps_host = urlparse(issuer).hostname
nrps_allowed_hosts = [h.strip() for h in os.getenv("MOCK_NRPS_ALLOWED_HOSTS", "").split(",") if h.strip()]
if not nrps_allowed_hosts and default_nrps_host:
    nrps_allowed_hosts = [default_nrps_host]
conf = {issuer: [{
    "default": True, "client_id": "mock-client",
    "auth_login_url": os.getenv("MOCK_AUTH_LOGIN_URL", f"{issuer}/auth"),
    "auth_token_url": os.getenv("MOCK_AUTH_TOKEN_URL", f"{issuer}/token"),
    "key_set_url": os.getenv("MOCK_KEY_SET_URL", f"{issuer}/jwks"),
    "private_key_file": "private.key", "public_key_file": "public.key",
    "deployment_ids": ["mock-deployment-1"],
    "nrps_allowed_hosts": nrps_allowed_hosts}]}
(cfg / output_name).write_text(json.dumps(conf, indent=2), encoding="utf-8")
os.chmod(cfg / output_name, 0o600)
print("Claves y configuración creadas en", cfg)
