"""Errors no API view handled are problems too, with the reference to quote (edge case #32)."""

import pytest
from django.test import Client

from apps.core.views import ConfigView

pytestmark = pytest.mark.django_db

PROBLEM_JSON = "application/problem+json"


def test_an_unknown_api_address_is_a_problem(client: Client) -> None:
    response = client.get("/api/v1/nothing-here/")

    body = response.json()
    assert (response.status_code, response["Content-Type"]) == (404, PROBLEM_JSON)
    assert body["detail"] == "There is nothing at this address."
    assert body["request_id"] == response["X-Request-ID"]


def test_elsewhere_a_missing_file_is_a_plain_404(client: Client) -> None:
    response = client.get("/static/nothing-here.js")

    assert response.status_code == 404
    assert PROBLEM_JSON not in response["Content-Type"]


def test_a_crash_is_a_problem_that_never_shows_the_error(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    def crash(*args: object, **kwargs: object) -> None:
        raise RuntimeError("salary 123456 for asha@acme.example")

    monkeypatch.setattr(ConfigView, "get", crash)
    client.raise_request_exception = False

    response = client.get("/api/v1/config/")

    body = response.json()
    assert (response.status_code, response["Content-Type"]) == (500, PROBLEM_JSON)
    assert body["detail"] == "Something went wrong on our side."
    assert body["request_id"] == response["X-Request-ID"]
    assert "asha" not in response.content.decode()
