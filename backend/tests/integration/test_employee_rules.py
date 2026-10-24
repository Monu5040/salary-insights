"""Rules the database enforces for employees (design §3; edge cases #8, #10, #12)."""

from decimal import Decimal
from typing import Any

import pytest
from django.db import IntegrityError, transaction

from tests.factories import employee

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "overrides",
    [
        {"full_name": "   "},
        {"employee_code": " "},
        {"salary": Decimal(0)},
        {"salary": Decimal(-1)},
    ],
    ids=["blank name", "blank code", "zero salary", "negative salary"],
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
