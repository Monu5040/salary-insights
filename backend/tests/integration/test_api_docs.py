from io import StringIO

import pytest
from django.core.management import call_command
from django.test import Client


@pytest.mark.django_db
def test_the_api_schema_is_published(client: Client) -> None:
    response = client.get("/api/schema/")

    assert response.status_code == 200
    assert b"openapi" in response.content


def test_the_schema_is_valid_openapi_without_warnings() -> None:
    # Keeps every endpoint described well enough for a generated client (design §7).
    call_command("spectacular", "--validate", "--fail-on-warn", stdout=StringIO())
