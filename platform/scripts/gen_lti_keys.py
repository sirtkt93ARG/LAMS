"""Crea el par de claves RSA de la herramienta LTI y la configuración para el LMS simulado."""
import json, pathlib, sys
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

cfg = pathlib.Path("lti_service/configs")
cfg.mkdir(parents=True, exist_ok=True)
if (cfg / "lti.mock.json").exists() and "--force" not in sys.argv:
    print("Ya existe lti_service/configs/lti.mock.json (usá --force para regenerar)."); sys.exit(0)
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
(cfg / "private.key").write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
                                                    serialization.NoEncryption()))
(cfg / "public.key").write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM,
                                                               serialization.PublicFormat.SubjectPublicKeyInfo))
conf = {"http://localhost:8300": [{
    "default": True, "client_id": "mock-client",
    "auth_login_url": "http://localhost:8300/auth", "auth_token_url": "http://localhost:8300/token",
    "key_set_url": "http://localhost:8300/jwks", "private_key_file": "private.key", "public_key_file": "public.key",
    "deployment_ids": ["mock-deployment-1"]}]}
(cfg / "lti.mock.json").write_text(json.dumps(conf, indent=2), encoding="utf-8")
print("Claves y configuración creadas en", cfg)
