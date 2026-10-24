"""Changing salary history (design §6; edge cases #41 to #45).

Every write locks the employee, checks the If-Match version and bumps it, like an edit to
the employee: the history is part of their record. Amounts are absolute: a % raise is turned
into the previewed amount before it is sent.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.compensation.models import SalaryRecord
from apps.core.errors import Conflict
from apps.employees.models import Employee
from apps.employees.services import lock_employee
from apps.reference.models import Currency
from domain.stats import Reason


def record_change(
    employee_id: int,
    version: int,
    *,
    effective_date: date,
    amount: Decimal,
    currency: Currency,
    reason: str,
    note: str = "",
) -> Employee:
    """Add a change, past or future. A future one counts from its date with no job (#42)."""
    try:
        with transaction.atomic():
            employee = lock_employee(employee_id, version)
            _after_hire(employee, effective_date)
            if reason == Reason.HIRE:
                raise ValidationError({"reason": ["Only the starting salary is a hire."]})
            SalaryRecord.objects.create(
                employee=employee,
                effective_date=effective_date,
                amount=amount,
                currency=currency,
                reason=reason,
                note=note,
            )
            _bump(employee)
    except IntegrityError as error:
        raise _same_day(error, employee_id, effective_date) from None
    return employee


def correct_record(
    employee_id: int, version: int, record_id: int, changes: dict[str, Any]
) -> Employee:
    """Fix a wrong entry. The starting salary stays a hire, dated on the hire date."""
    new_date = changes.get("effective_date")
    try:
        with transaction.atomic():
            employee = lock_employee(employee_id, version)
            entry = _entry(employee, record_id)
            moved = new_date is not None and new_date != entry.effective_date
            if entry.reason == Reason.HIRE and (
                moved or changes.get("reason", Reason.HIRE) != Reason.HIRE
            ):
                raise ValidationError(
                    "The starting salary stays a hire on the hire date. "
                    "To move it, change the employee's hire date."
                )
            if entry.reason != Reason.HIRE and changes.get("reason") == Reason.HIRE:
                raise ValidationError({"reason": ["Only the starting salary is a hire."]})
            if moved:
                _after_hire(employee, changes["effective_date"])
            before = _values(entry)
            for name, value in changes.items():
                setattr(entry, name, value)
            if _values(entry) == before:
                return employee  # nothing new: no version bump
            entry.save()
            _bump(employee)
    except IntegrityError as error:
        raise _same_day(error, employee_id, new_date) from None
    return employee


def remove_record(employee_id: int, version: int, record_id: int) -> Employee:
    """Remove a wrong or no longer planned change. The starting salary can only be corrected."""
    with transaction.atomic():
        employee = lock_employee(employee_id, version)
        entry = _entry(employee, record_id)
        if entry.reason == Reason.HIRE:
            raise ValidationError("The starting salary can't be removed. Correct it instead.")
        entry.delete()
        _bump(employee)
    return employee


def _entry(employee: Employee, record_id: int) -> SalaryRecord:
    return get_object_or_404(
        SalaryRecord.objects.select_related("currency"), pk=record_id, employee=employee
    )


def _after_hire(employee: Employee, day: date) -> None:
    """No salary before the hire date (edge case #41)."""
    if day < employee.hire_date:
        message = f"Pick a date on or after the hire date, {employee.hire_date}."
        raise ValidationError({"effective_date": [message]})


def _bump(employee: Employee) -> None:
    employee.version += 1
    employee.save(update_fields=["version", "updated_at"])


def _values(entry: SalaryRecord) -> tuple[Any, ...]:
    return (entry.effective_date, entry.amount, entry.currency_id, entry.reason, entry.note)


def _same_day(error: IntegrityError, employee_id: int, day: date | None) -> Exception:
    """A second change on one day is a 409 pointing at the first (edge case #43)."""
    constraint = getattr(getattr(error.__cause__, "diag", None), "constraint_name", None)
    if constraint != "salary_record_one_per_day" or day is None:
        return error
    existing = (
        SalaryRecord.objects.filter(employee_id=employee_id, effective_date=day)
        .values_list("pk", flat=True)
        .first()
    )
    message = f"There's already a salary change on {day}. Correct that one instead."
    return Conflict(message, errors={"effective_date": [message]}, existing_id=existing)
