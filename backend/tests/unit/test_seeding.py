"""The demo data generator (design §12): deterministic, valid and realistic."""

import importlib
import unicodedata
from datetime import date
from decimal import Decimal

from apps.employees import seeding

AS_OF = date(2026, 9, 30)
PEOPLE = seeding.generate(2000, seed=7, as_of=AS_OF)
REFERENCE = importlib.import_module("apps.reference.migrations.0002_reference_data")
CEILINGS = {code: Decimal(ceiling) for code, _name, _minor, ceiling, _rate in REFERENCE.CURRENCIES}


def test_the_same_seed_gives_identical_data() -> None:
    assert seeding.generate(50, seed=7, as_of=AS_OF) == seeding.generate(50, seed=7, as_of=AS_OF)


def test_a_different_seed_gives_different_data() -> None:
    assert seeding.generate(50, seed=7, as_of=AS_OF) != seeding.generate(50, seed=8, as_of=AS_OF)


def test_everyone_is_paid_in_the_currency_of_their_country() -> None:
    for person in PEOPLE:
        assert person.currency == seeding.COUNTRIES[person.country].currency


def test_amounts_are_positive_round_and_under_the_currency_ceiling() -> None:
    for person in PEOPLE:
        assert 0 < person.salary <= CEILINGS[person.currency]
        assert person.salary % seeding.SALARY_STEPS[person.currency] == 0


def test_everyone_was_hired_on_or_before_the_as_of_date() -> None:
    assert all(seeding.FIRST_HIRE <= person.hire_date <= AS_OF for person in PEOPLE)


def test_the_rates_match_the_reference_data() -> None:
    rates = {code: Decimal(rate) for code, _name, _minor, _ceiling, rate in REFERENCE.CURRENCIES}
    assert rates == seeding.FX_RATES


def test_departments_match_the_reference_data() -> None:
    assert set(seeding.DEPARTMENTS) == set(REFERENCE.DEPARTMENTS)


def test_names_are_normalized_and_any_script_is_kept() -> None:
    names = [person.full_name for person in PEOPLE]
    assert all(unicodedata.is_normalized("NFC", name) for name in names)
    assert any(not name.isascii() for name in names)
