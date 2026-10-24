"""Security headers on every response, and pages that keep to the policy (edge case #29)."""

import re

import pytest
from django.http.response import HttpResponseBase
from django.test import Client

pytestmark = pytest.mark.django_db


def policy(response: HttpResponseBase) -> dict[str, list[str]]:
    directives: dict[str, list[str]] = {}
    for part in response["Content-Security-Policy"].split(";"):
        name, *values = part.split()
        directives[name] = values
    return directives


@pytest.mark.parametrize("path", ["/api/v1/config/", "/healthz/", "/employees"])
def test_every_response_carries_the_policy(client: Client, path: str) -> None:
    response = client.get(path)

    csp = policy(response)
    assert csp["default-src"] == ["'self'"]
    assert csp["script-src"] == ["'self'"]  # no inline scripts, nothing from elsewhere
    assert csp["style-src"] == ["'self'", "'unsafe-inline'"]  # Ant Design injects its styles
    assert csp["object-src"] == csp["base-uri"] == csp["frame-ancestors"] == ["'none'"]
    assert csp["form-action"] == ["'self'"]
    assert response["X-Frame-Options"] == "DENY"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Referrer-Policy"] == "same-origin"
    assert response["Cross-Origin-Opener-Policy"] == "same-origin"


def test_the_api_docs_run_under_the_policy(client: Client) -> None:
    page = client.get("/api/docs/").content.decode()

    scripts = re.findall(r"<script[^>]*>", page)
    assert scripts and all(" src=" in tag for tag in scripts)  # no inline script
    assert "cdn.jsdelivr.net" not in page  # served from our own static files
    started = client.get("/api/docs/?script")
    assert (started.status_code, started["Content-Type"]) == (200, "application/javascript")
