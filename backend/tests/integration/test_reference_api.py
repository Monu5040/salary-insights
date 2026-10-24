"""Reference lists and settings for filters and forms (design §2, §7)."""

from datetime import date

import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


def test_countries_come_with_their_currency_and_locale(client: Client) -> None:
    countries = client.get("/api/v1/reference/countries/").json()

    india = next(country for country in countries if country["code"] == "IN")
    assert india == {"code": "IN", "name": "India", "default_currency": "INR", "locale": "en-IN"}


def test_currencies_say_how_many_decimals_they_have_and_their_rate(client: Client) -> None:
    currencies = {row["code"]: row for row in client.get("/api/v1/reference/currencies/").json()}

    assert (currencies["JPY"]["minor_units"], currencies["KWD"]["minor_units"]) == (0, 3)
    assert currencies["EUR"]["usd_per_unit"] == "1.0800000000"


def test_departments_are_listed_by_name(client: Client) -> None:
    names = [row["name"] for row in client.get("/api/v1/reference/departments/").json()]

    assert names == sorted(names) and "Engineering" in names


def test_api_responses_are_never_kept_by_shared_caches(client: Client) -> None:
    response = client.get("/api/v1/reference/countries/")
    assert set(response["Cache-Control"].split(", ")) == {"private", "no-cache"}


def test_the_screens_get_the_settings_they_follow(client: Client, today: date) -> None:
    config = client.get("/api/v1/config/").json()

    assert config == {"reporting_currency": "USD", "today": "2026-09-30"}
