"""Local development: debug on and local hosts."""

from .base import *

ENVIRONMENT = "dev"
DEBUG = True
SECRET_KEY = "dev-only-not-a-secret"
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
