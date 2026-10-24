"""Rules the database enforces for employees (design §3; edge cases #8, #10, #12)."""

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.db import IntegrityError, transaction

from tests.factories import employee, record

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "overrides",
    [
        {"full_name": "   "},
        {"employee_code": " "},
    ],
    ids=["blank name", "blank code"],
)
def test_the_database_rejects_an_invalid_employee(overrides: dict[str, Any]) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        employee(**overrides)


def test_email_is_unique_ignoring_case() -> None:
    employee(email="Asha.Rao@ACME.example")
    with pytest.raises(IntegrityError), transaction.atomic():
        employee(email="asha.rao@acme.example")


def test_employee_code_is_unique() -> None:
    employee(employee_code="E00042")
    with pytest.raises(IntegrityError), transaction.atomic():
        employee(employee_code="E00042")


@pytest.mark.parametrize("amount", ["0", "-1"])
def test_a_salary_must_be_more_than_zero(amount: str) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        employee(salary=amount)


def test_a_salary_needs_a_known_reason() -> None:
    person = employee()
    with pytest.raises(IntegrityError), transaction.atomic():
        record(person, effective_date=date(2025, 1, 1), reason="bonus")


def test_one_salary_change_per_employee_per_day() -> None:
    person = employee()
    with pytest.raises(IntegrityError), transaction.atomic():
        record(person, amount=Decimal("1900000"), reason="merit")
