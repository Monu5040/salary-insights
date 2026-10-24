"""Tests: a fixed secret and plain static storage."""

from .base import *

ENVIRONMENT = "test"
SECRET_KEY = "test-only-not-a-secret"
STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
# Look files up per request, as in development: tests never run collectstatic.
WHITENOISE_AUTOREFRESH = True
