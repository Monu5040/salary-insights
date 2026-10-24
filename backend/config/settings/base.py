"""Settings shared by every environment. Anything that differs per deploy comes from env vars."""

from pathlib import Path

import dj_database_url
import django_stubs_ext

from config.env import env_int, env_str

# Lets generic classes such as QuerySet[Model] be subscripted at runtime, for typing.
django_stubs_ext.monkeypatch()

BASE_DIR = Path(__file__).resolve().parents[2]

# Which deployment this is. The seed command runs only in dev, test and demo (edge case #30).
ENVIRONMENT = env_str("ENV", "unknown")
# The build of the code running, such as a git commit, for telling deploys apart.
RELEASE = env_str("RELEASE", "dev")

DEBUG = False
ALLOWED_HOSTS: list[str] = []

# No sign-in (requirements: one HR Manager persona, no authentication), so no admin, sessions
# or users. contenttypes and auth stay only because DRF imports them.
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "apps.core",
    "apps.reference",
    "apps.employees",
    "apps.analytics",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.core.middleware.RequestIdMiddleware",
    "apps.core.middleware.PrivateApiCacheMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    # Nothing here signs in, and DRF's views are exempt; kept so no non-API form is ever open.
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": ["django.template.context_processors.request"],
        },
    },
]

# PostgreSQL. gunicorn's gthread timeout doesn't bound a request, so Postgres does (design §10).
_database = dj_database_url.parse(
    env_str("DATABASE_URL", "postgres://acme:acme@localhost:5432/acme"),
    conn_health_checks=True,
)
_timeouts = {
    "statement_timeout": env_str("DB_STATEMENT_TIMEOUT", "10s"),
    "lock_timeout": env_str("DB_LOCK_TIMEOUT", "8s"),
    "idle_in_transaction_session_timeout": env_str("DB_IDLE_IN_TRANSACTION_TIMEOUT", "60s"),
}
_database["OPTIONS"] = {
    **_database.get("OPTIONS", {}),
    "options": " ".join(f"-c {name}={value}" for name, value in _timeouts.items()),
}
DATABASES = {"default": _database}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# The built React app (`npm run build`): its hashed files are static files, and its page is
# served by apps.core.views.spa for every address the app handles (design §2).
SPA_DIR = Path(env_str("SPA_DIR", str(BASE_DIR.parent / "frontend" / "dist")))
STATICFILES_DIRS = [SPA_DIR] if SPA_DIR.is_dir() else []
# Files named after a hash of their contents are cached for good: the app's (Vite names them
# assets/name-<hash>.js) and, in production, Django's own (name.<hash>.css).
WHITENOISE_IMMUTABLE_FILE_TEST = r"^/static/assets/.+-[\w-]{8}\.\w+$|\.[0-9a-f]{12}\.\w+$"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

REST_FRAMEWORK = {
    # Open to anyone who can reach it: the brief asks for no authentication (requirements).
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.errors.exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "ACME Salary API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # Swagger UI from our own static files, not a CDN, so the docs keep to the CSP.
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
}

# Working assumptions (design §2 Configuration), as agreed in docs/00-clarifying-questions.md.
# A different answer changes these values, not code. Exchange rates are reference data.
REPORTING_CURRENCY = env_str("REPORTING_CURRENCY", "USD")
MIN_GROUP_SIZE = env_int("MIN_GROUP_SIZE", 5)
ORG_TIME_ZONE = env_str("ORG_TIME_ZONE", "UTC")
