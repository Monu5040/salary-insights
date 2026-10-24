"""Production: secrets and hosts from the environment, HTTPS behind the TLS proxy (Caddy).

See design §9 (Settings) and §10 (Deployment).
"""

from config.env import env_bool, env_int, env_list, env_str

from .base import *

# The public demo runs these settings with ENV=demo, which lets the nightly reseed run.
ENVIRONMENT = env_str("ENV", "production")
SECRET_KEY = env_str("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")

# Caddy terminates TLS and sets X-Forwarded-Proto.
if env_bool("DJANGO_BEHIND_TLS_PROXY", True):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
# Health probes use plain HTTP. Django matches these without the leading slash.
SECURE_REDIRECT_EXEMPT = [r"^healthz/", r"^readyz/"]
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env_int("DJANGO_HSTS_SECONDS", 3600)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = env_bool("DJANGO_HSTS_PRELOAD", False)
if not SECURE_HSTS_PRELOAD:
    # Joining the browser preload list is the domain owner's decision, not the app's.
    SILENCED_SYSTEM_CHECKS = ["security.W021"]

DATABASES["default"]["OPTIONS"]["pool"] = {
    "min_size": 2,
    "max_size": env_int("DB_POOL_MAX_SIZE", 4),
    "timeout": 5,
}
