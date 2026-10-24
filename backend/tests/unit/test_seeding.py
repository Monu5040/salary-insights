"""The demo data generator (design §12): deterministic, valid and realistic."""

import importlib
import unicodedata
from datetime import date
from decimal import Decimal

from apps.employees import seeding
from domain.stats import Reason

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
        currency = seeding.COUNTRIES[person.country].currency
        assert {salary.currency for salary in person.salaries} == {currency}


def test_amounts_are_positive_round_and_under_the_currency_ceiling() -> None:
    for person in PEOPLE:
        for salary in person.salaries:
            assert 0 < salary.amount <= CEILINGS[salary.currency]
            assert salary.amount % seeding.SALARY_STEPS[salary.currency] == 0


def test_every_history_starts_with_the_hire_and_moves_forward() -> None:
    for person in PEOPLE:
        first = person.salaries[0]
        assert (first.reason, first.effective_date) == (Reason.HIRE, person.hire_date)
        days = [salary.effective_date for salary in person.salaries]
        assert days == sorted(set(days))


def test_the_mix_includes_promotions_and_future_dated_raises() -> None:
    reasons = {salary.reason for person in PEOPLE for salary in person.salaries}
    assert {Reason.HIRE, Reason.MERIT, Reason.PROMOTION, Reason.MARKET} <= reasons
    assert any(s.effective_date > AS_OF for person in PEOPLE for s in person.salaries)


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
