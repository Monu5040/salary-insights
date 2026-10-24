"""The working assumptions (design §2 Configuration): defaults and startup validation."""

from decimal import Decimal

import pytest
from pytest_django.fixtures import Settings

from apps.core.checks import check_working_assumptions


def error_ids() -> list[str | None]:
    return [error.id for error in check_working_assumptions(None)]


def test_defaults_match_the_design(settings: Settings) -> None:
    assert settings.REPORTING_CURRENCY == "USD"
    assert settings.MIN_GROUP_SIZE == 5
    assert settings.ORG_TIME_ZONE == "UTC"
    assert (Decimal("0.80"), Decimal("1.20")) == settings.PAY_EQUITY_BAND
    assert error_ids() == []


@pytest.mark.parametrize("currency", ["usd", "US", "USDX", "U5D"])
def test_reporting_currency_must_be_an_iso_code(settings: Settings, currency: str) -> None:
    settings.REPORTING_CURRENCY = currency
    assert error_ids() == ["acme.E001"]


def test_org_time_zone_must_exist(settings: Settings) -> None:
    settings.ORG_TIME_ZONE = "Mars/Olympus_Mons"
    assert error_ids() == ["acme.E002"]


@pytest.mark.parametrize(
    "name", ["MIN_GROUP_SIZE", "GROQ_TIMEOUT_SECONDS", "IMPORT_MAX_MB", "IMPORT_MAX_ROWS"]
)
def test_limits_must_be_at_least_one(settings: Settings, name: str) -> None:
    setattr(settings, name, 0)
    assert error_ids() == ["acme.E003"]


@pytest.mark.parametrize(
    ("low", "high"), [("1.10", "1.20"), ("0.80", "0.90"), ("0", "1.20"), ("1.20", "0.80")]
)
def test_the_pay_equity_band_sits_either_side_of_one(
    settings: Settings, low: str, high: str
) -> None:
    settings.PAY_EQUITY_BAND = (Decimal(low), Decimal(high))
    assert error_ids() == ["acme.E004"]
