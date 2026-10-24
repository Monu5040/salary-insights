"""Reference data: what every environment starts with, and the rules the database enforces."""

from collections.abc import Callable
from decimal import Decimal

import pytest
from django.db import IntegrityError, models, transaction

from apps.reference.models import Country, Currency, Department

pytestmark = pytest.mark.django_db


def test_every_environment_starts_with_currencies_countries_and_departments() -> None:
    assert Currency.objects.get(code="JPY").minor_units == 0
    assert Currency.objects.get(code="KWD").minor_units == 3
    assert Country.objects.get(code="IN").default_currency_id == "INR"
    assert Department.objects.filter(name="Engineering").exists()


def test_every_currency_has_a_fixed_rate_and_usd_is_one() -> None:
    assert Currency.objects.get(code="USD").usd_per_unit == Decimal(1)
    assert not Currency.objects.filter(usd_per_unit__lte=0).exists()


@pytest.mark.parametrize(
    "build",
    [
        lambda: Currency(code="usd", name="x", minor_units=2, salary_ceiling=1, usd_per_unit=1),
        lambda: Currency(code="XYZ", name="x", minor_units=5, salary_ceiling=1, usd_per_unit=1),
        lambda: Currency(code="XYZ", name="x", minor_units=2, salary_ceiling=0, usd_per_unit=1),
        lambda: Currency(code="XYZ", name="x", minor_units=2, salary_ceiling=1, usd_per_unit=0),
        lambda: Country(code="in", name="Lowercase", default_currency_id="INR", locale="en"),
        lambda: Department(name="Engineering"),
    ],
    ids=[
        "currency code not ISO",
        "more minor units than storage",
        "ceiling not positive",
        "rate not positive",
        "country code not ISO",
        "two departments share a name",
    ],
)
def test_the_database_rejects_invalid_reference_data(build: Callable[[], models.Model]) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        build().save()
