from unittest.mock import patch

import pytest
from django.db import OperationalError, connection
from django.test import Client

from apps.core.health import database_is_reachable


def test_healthz_answers_without_touching_the_database(client: Client) -> None:
    response = client.get("/healthz/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "no-cache" in response["Cache-Control"]


@pytest.mark.django_db
def test_readyz_is_ok_when_the_database_answers(client: Client) -> None:
    response = client.get("/readyz/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_is_unavailable_when_the_database_is_down(client: Client) -> None:
    with patch("apps.core.views.database_is_reachable", return_value=False):
        response = client.get("/readyz/")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_a_failing_query_means_the_database_is_unreachable() -> None:
    with patch.object(connection, "cursor", side_effect=OperationalError("down")):
        assert database_is_reachable() is False


@pytest.mark.parametrize("path", ["/healthz/", "/readyz/"])
def test_probes_only_accept_get(client: Client, path: str) -> None:
    assert client.post(path).status_code == 405
