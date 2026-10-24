"""Changing employees (design §7; edge cases #10, #14 to #16).

Each change is one transaction: lock the employee, check the version the client loaded,
apply the rules and bump the version.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.compensation.models import SalaryRecord
from apps.core.errors import Conflict, PreconditionFailed
from apps.employees.models import Employee
from apps.reference.models import Currency
from domain.stats import Reason
from domain.text import fold

# Database constraints behind a 409, and the field each one protects (edge case #10).
_UNIQUE = {"employees_employee_code_key": "employee_code", "employee_email_unique_ci": "email"}


def create_employee(fields: dict[str, Any], salary: Decimal, currency: Currency) -> Employee:
    """Save the employee and their starting salary, dated on the hire date, or nothing."""
    employee = Employee(**fields)
    employee.search_text = _search_text(employee)
    try:
        with transaction.atomic():
            employee.save()
            SalaryRecord.objects.create(
                employee=employee,
                effective_date=employee.hire_date,
                amount=salary,
                currency=currency,
                reason=Reason.HIRE,
            )
    except IntegrityError as error:
        raise _conflict(error, fields) from None
    return employee


def update_employee(employee_id: int, version: int, changes: dict[str, Any]) -> Employee:
    """Apply an edit. A starting salary dated on the hire date moves with it. An edit that
    changes nothing keeps the version."""
    try:
        with transaction.atomic():
            employee = lock_employee(employee_id, version)
            changed = {
                name: value for name, value in changes.items() if getattr(employee, name) != value
            }
            if not changed:
                return employee
            if "hire_date" in changed:
                _move_hire_date(employee, changed["hire_date"])
            for name, value in changed.items():
                setattr(employee, name, value)
            employee.search_text = _search_text(employee)
            employee.version += 1
            employee.save()
    except IntegrityError as error:
        raise _conflict(error, changes) from None
    return employee


def delete_employee(employee_id: int, version: int) -> None:
    """Remove someone who left or was added by mistake, unless the record changed since."""
    with transaction.atomic():
        lock_employee(employee_id, version).delete()


def lock_employee(employee_id: int, version: int) -> Employee:
    """Lock the employee row, then check the client saw its latest version (edge case #15).

    Only the employee row is locked (`of`), not the rows joined to it.
    """
    rows = Employee.objects.select_for_update(of=("self",)).select_related("country", "department")
    employee = get_object_or_404(rows, pk=employee_id)
    if employee.version != version:
        raise PreconditionFailed(
            "Someone else changed this employee since you opened it. Reload to see their changes.",
            current_version=employee.version,
        )
    return employee


def _move_hire_date(employee: Employee, new_date: date) -> None:
    """Keep the salary history inside employment (edge case #45)."""
    records = list(employee.salary_records.order_by("effective_date")[:2])
    if not records:
        return
    first, following = records[0], records[1:]
    if first.reason == Reason.HIRE and first.effective_date == employee.hire_date:
        # The salary they were hired on moves with the hire date, if it stays first.
        if following and new_date >= following[0].effective_date:
            message = f"Pick a date before the salary change on {following[0].effective_date}."
            raise ValidationError({"hire_date": [message]})
        first.effective_date = new_date
        first.save(update_fields=["effective_date"])
    elif new_date > first.effective_date:
        raise ValidationError(
            {"hire_date": [f"Pick a date on or before the first salary, {first.effective_date}."]}
        )


def _conflict(error: IntegrityError, fields: dict[str, Any]) -> Exception:
    """A duplicate code or email as a 409 that names the field and the employee holding it.

    Other integrity errors are bugs the serializers should have caught: they stay errors.
    """
    constraint = getattr(getattr(error.__cause__, "diag", None), "constraint_name", None)
    field = _UNIQUE.get(constraint or "")
    if field is None:
        return error
    holder = (
        Employee.objects.filter(employee_code=fields[field])
        if field == "employee_code"
        else Employee.objects.filter(email__iexact=fields[field])
    )
    label = "employee code" if field == "employee_code" else "email"
    message = f"Another employee already has this {label}."
    existing_id = holder.values_list("pk", flat=True).first()
    return Conflict(message, errors={field: [message]}, existing_id=existing_id)


def _search_text(employee: Employee) -> str:
    return fold(f"{employee.full_name} {employee.employee_code}")
