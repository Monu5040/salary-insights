"""The working assumptions (design §2 Configuration): defaults and startup validation."""

import pytest
from pytest_django.fixtures import Settings

from apps.core.checks import check_working_assumptions


def error_ids() -> list[str | None]:
    return [error.id for error in check_working_assumptions(None)]


def test_defaults_match_the_design(settings: Settings) -> None:
    assert settings.REPORTING_CURRENCY == "USD"
    assert settings.MIN_GROUP_SIZE == 5
    assert settings.ORG_TIME_ZONE == "UTC"
    assert error_ids() == []


@pytest.mark.parametrize("currency", ["usd", "US", "USDX", "U5D"])
def test_reporting_currency_must_be_an_iso_code(settings: Settings, currency: str) -> None:
    settings.REPORTING_CURRENCY = currency
    assert error_ids() == ["acme.E001"]


def test_org_time_zone_must_exist(settings: Settings) -> None:
    settings.ORG_TIME_ZONE = "Mars/Olympus_Mons"
    assert error_ids() == ["acme.E002"]


def test_the_minimum_group_size_must_be_at_least_one(settings: Settings) -> None:
    settings.MIN_GROUP_SIZE = 0
    assert error_ids() == ["acme.E003"]
