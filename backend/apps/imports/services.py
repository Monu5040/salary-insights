"""Importing a sheet in two steps, preview then apply, with nothing stored between them
(design §6; edge cases #46 to #48).

Preview reads the file and works out the plan. Apply gets the same file back with the plan's
fingerprint, locks the employees it touches, plans again, and applies only an identical plan,
in one transaction: the whole file or nothing.
"""

from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.compensation.models import SalaryRecord
from apps.core.bulk import update_many
from apps.core.errors import Conflict
from apps.employees.models import Employee
from apps.imports.planning import Plan, plan_import
from domain.importing import FileError, Sheet, read_sheet
from domain.text import fold

PREVIEW_ROWS = 100  # of each kind
ERROR_ROWS = 500


@dataclass(frozen=True)
class Applied:
    creates: int
    changes: int
    unchanged: int


def preview(content: bytes, date_format: str) -> dict[str, Any]:
    """What the file would change, and every problem in it, without changing anything."""
    sheet = _read(content, date_format)
    return _shown(sheet, plan_import(sheet))


def apply(content: bytes, date_format: str, fingerprint: str) -> Applied:
    """Apply the plan the uploader confirmed, or nothing (edge case #47)."""
    sheet = _read(content, date_format)
    with transaction.atomic():
        codes = sorted({row.employee_code for row in sheet.rows})
        list(Employee.objects.select_for_update().filter(employee_code__in=codes).order_by("pk"))
        plan = plan_import(sheet)
        if plan.errors:
            raise ValidationError(
                "Some rows have errors, and the file is imported whole or not at all. "
                "Fix them in the sheet and upload it again."
            )
        if plan.fingerprint() != fingerprint:
            raise Conflict(
                "Some employees in this file changed after the preview. Preview it again.",
                preview=_shown(sheet, plan),
            )
        _apply(plan)
    return Applied(len(plan.creates), len(plan.changes), plan.unchanged)


def _read(content: bytes, date_format: str) -> Sheet:
    """Too big or too long is refused before any row is read (edge case #46)."""
    limit = settings.IMPORT_MAX_MB * 1024 * 1024
    if len(content) > limit:
        megabytes = len(content) / 1024 / 1024
        message = f"The file is {megabytes:.1f} MB; the most is {settings.IMPORT_MAX_MB} MB."
        raise ValidationError({"file": [message]})
    try:
        return read_sheet(content, date_format=date_format, max_rows=settings.IMPORT_MAX_ROWS)
    except FileError as error:
        raise ValidationError({"file": [str(error)]}) from None


def _plain(value: Any) -> Any:
    """A value as JSON keeps it: decimals and dates as text."""
    return value if value is None or isinstance(value, str | int | bool) else str(value)


def _shown(sheet: Sheet, plan: Plan) -> dict[str, Any]:
    """The plan as the preview shows it: counts, the first rows of each kind, the errors."""
    return {
        "rows": len(sheet.rows) + len({error.line for error in sheet.errors}),
        "creates": len(plan.creates),
        "changes": len(plan.changes),
        "unchanged": plan.unchanged,
        "error_rows": len({error.line for error in plan.errors}),
        "ignored_columns": sheet.ignored_columns,
        "new_employees": [
            {
                "line": create.line,
                "employee_code": create.employee_code,
                "full_name": create.values["full_name"],
                "salary": create.salary.text(),
            }
            for create in plan.creates[:PREVIEW_ROWS]
        ],
        "changed_employees": [
            {
                "line": change.line,
                "employee_code": change.employee_code,
                "full_name": change.full_name,
                "fields": {
                    name: [_plain(before), _plain(after)]
                    for name, (before, after) in change.shown.items()
                },
                "salary": change.salary.text() if change.salary else None,
            }
            for change in plan.changes[:PREVIEW_ROWS]
        ],
        "row_errors": [
            {"line": error.line, "column": error.column, "message": error.message}
            for error in plan.errors[:ERROR_ROWS]
        ],
        "fingerprint": plan.fingerprint(),
    }


def _apply(plan: Plan) -> None:
    """Every change in the plan, set-based: bulk inserts, and one update for every changed
    employee (design §10)."""
    created = Employee.objects.bulk_create(
        [
            Employee(
                **new.values, search_text=fold(f"{new.values['full_name']} {new.employee_code}")
            )
            for new in plan.creates
        ],
        batch_size=2000,
    )
    salaries = [
        SalaryRecord(
            employee=employee,
            effective_date=new.salary.effective_date,
            amount=new.salary.amount,
            currency_id=new.salary.currency,
            reason=new.salary.reason,
        )
        for employee, new in zip(created, plan.creates, strict=True)
    ]
    changed = Employee.objects.in_bulk([change.employee_id for change in plan.changes])
    fields = {"version", "updated_at"}
    now = timezone.now()
    for change in plan.changes:
        employee = changed[change.employee_id]
        for name, value in change.values.items():
            setattr(employee, name, value)
            fields.add(name)
        if "full_name" in change.values:
            employee.search_text = fold(f"{employee.full_name} {employee.employee_code}")
            fields.add("search_text")
        employee.version += 1  # a salary change is a change to the employee too
        employee.updated_at = now
        if change.salary is not None:
            salaries.append(
                SalaryRecord(
                    employee=employee,
                    effective_date=change.salary.effective_date,
                    amount=change.salary.amount,
                    currency_id=change.salary.currency,
                    reason=change.salary.reason,
                    note="Imported",
                )
            )
    update_many(list(changed.values()), sorted(fields))
    SalaryRecord.objects.bulk_create(salaries, batch_size=5000)
