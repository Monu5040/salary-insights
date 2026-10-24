"""What an import would change (design §6).

The same plan is the preview the uploader confirms and the work apply does. It is worked out
set-based: a fixed handful of queries whatever the file's size. Rows with errors are left out
of the plan and reported.
"""

import hashlib
import json
from bisect import bisect_right
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.functions import Lower

from apps.compensation.models import SalaryRecord
from apps.employees.models import Employee
from apps.reference.models import Country, Currency, Department
from domain.importing import Row, RowError, SalaryCells, Sheet
from domain.money import InvalidAmount, parse_amount
from domain.stats import Reason

# Fields an import can set on an employee, as the model names them.
FIELDS = ("full_name", "email", "country_id", "department_id", "job_title", "hire_date")
# How the preview names them.
LABELS = {"country_id": "country", "department_id": "department"}


@dataclass(frozen=True)
class NewSalary:
    effective_date: date
    amount: Decimal
    currency: str
    reason: str

    def text(self) -> str:
        return f"{self.amount} {self.currency} from {self.effective_date} ({self.reason})"


@dataclass(frozen=True)
class NewEmployee:
    line: int
    employee_code: str
    values: dict[str, Any]  # model field → value, ready for Employee(**values)
    shown: dict[str, Any]  # field as the preview names it → value as it shows it
    salary: NewSalary


@dataclass(frozen=True)
class Change:
    line: int
    employee_id: int
    employee_code: str
    full_name: str
    values: dict[str, Any]  # model field → new value, only those that change
    shown: dict[str, tuple[Any, Any]]  # field as the preview names it → (before, after)
    salary: NewSalary | None


@dataclass
class Plan:
    creates: list[NewEmployee] = field(default_factory=list)
    changes: list[Change] = field(default_factory=list)
    unchanged: int = 0
    errors: list[RowError] = field(default_factory=list)
    versions: dict[int, int] = field(default_factory=dict)  # employee → version planned on

    def fingerprint(self) -> str:
        """What the uploader confirmed. Apply re-plans under locks and goes ahead only when
        this still matches, so nobody's later change is overwritten (edge case #47)."""
        content = {
            "creates": [asdict(create) for create in self.creates],
            "changes": [asdict(change) for change in self.changes],
            "versions": sorted(self.versions.items()),
        }
        encoded = json.dumps(content, cls=DjangoJSONEncoder, sort_keys=True)
        return hashlib.sha256(encoded.encode()).hexdigest()


class _References:
    """Countries, departments and currencies, each loaded with one query."""

    def __init__(self) -> None:
        self.countries = set(Country.objects.values_list("code", flat=True))
        departments = Department.objects.values_list("name", "id")
        self.departments = {name.casefold(): pk for name, pk in departments}
        self.department_names = {pk: name for name, pk in departments}
        self.currencies = {
            code: (minor_units, ceiling)
            for code, minor_units, ceiling in Currency.objects.values_list(
                "code", "minor_units", "salary_ceiling"
            )
        }

    def shown(self, name: str, value: Any) -> Any:
        """A value as the preview shows it: departments by name, not id."""
        if name == "department_id":
            return self.department_names.get(value, value)
        return value


def plan_import(sheet: Sheet) -> Plan:
    plan = Plan(errors=list(sheet.errors))
    if not sheet.rows:
        return plan
    references = _References()
    codes = [row.employee_code for row in sheet.rows]
    on_file = {
        employee.employee_code: employee
        for employee in Employee.objects.filter(employee_code__in=codes)
    }
    emails = {row.email.casefold() for row in sheet.rows}
    email_owners = dict(
        Employee.objects.annotate(folded=Lower("email"))
        .filter(folded__in=emails)
        .values_list("folded", "employee_code")
    )
    history: dict[int, list[SalaryRecord]] = defaultdict(list)
    for record in SalaryRecord.objects.filter(
        employee_id__in=[employee.pk for employee in on_file.values()]
    ).order_by("employee_id", "effective_date"):
        history[record.employee_id].append(record)

    for row in sheet.rows:
        errors: list[RowError] = []
        values = _values(row, references, errors)
        owner = email_owners.get(row.email.casefold())
        if owner is not None and owner != row.employee_code:
            errors.append(RowError(row.line, "email", f"Already the email of employee {owner}."))
        employee = on_file.get(row.employee_code)
        if employee is None:
            create = _new_employee(row, values, references, errors)
            if not errors and create is not None:
                plan.creates.append(create)
        else:
            plan.versions[employee.pk] = employee.version
            change = _change(row, employee, values, history[employee.pk], references, errors)
            if not errors and change is None:
                plan.unchanged += 1
            elif not errors and change is not None:
                plan.changes.append(change)
        plan.errors += errors
    plan.errors.sort(key=lambda error: (error.line, error.column))
    return plan


def _values(row: Row, references: _References, errors: list[RowError]) -> dict[str, Any]:
    """The row as model values, with each unknown reference an error (edge case #13)."""
    if row.country not in references.countries:
        errors.append(RowError(row.line, "country", f"No country with the code {row.country}."))
    department = references.departments.get(row.department.casefold())
    if department is None:
        names = ", ".join(sorted(references.department_names.values()))
        message = f"No department called {row.department}. Use one of: {names}."
        errors.append(RowError(row.line, "department", message))
    return {
        "full_name": row.full_name,
        "email": row.email,
        "country_id": row.country,
        "department_id": department,
        "job_title": row.job_title,
        "hire_date": row.hire_date,
    }


def _amount(
    line: int, salary: SalaryCells, references: _References, errors: list[RowError]
) -> Decimal | None:
    """A salary checked against its currency: decimals and typo ceiling (edge cases #2, #7)."""
    currency = references.currencies.get(salary.currency)
    if currency is None:
        errors.append(RowError(line, "currency", f"No currency {salary.currency}."))
        return None
    minor_units, ceiling = currency
    try:
        return parse_amount(salary.amount, minor_units, ceiling)
    except InvalidAmount as error:
        errors.append(RowError(line, "salary", str(error)))
        return None


def _new_employee(
    row: Row, values: dict[str, Any], references: _References, errors: list[RowError]
) -> NewEmployee | None:
    if row.salary is None:
        message = "A new employee needs a salary, currency and effective date."
        errors.append(RowError(row.line, "salary", message))
        return None
    amount = _amount(row.line, row.salary, references, errors)
    if amount is None or errors:
        return None
    # A first record dates from the day given, or the hire date if that is later: someone
    # loaded who starts next month is paid from their first day (edge case #41).
    starts = max(row.salary.effective_date, row.hire_date)
    salary = NewSalary(starts, amount, row.salary.currency, Reason.HIRE)
    shown = {
        LABELS.get(name, name): references.shown(name, value) for name, value in values.items()
    }
    values = {**values, "employee_code": row.employee_code}
    return NewEmployee(row.line, row.employee_code, values, shown, salary)


def _change(
    row: Row,
    employee: Employee,
    values: dict[str, Any],
    records: list[SalaryRecord],
    references: _References,
    errors: list[RowError],
) -> Change | None:
    changed = {name: value for name, value in values.items() if getattr(employee, name) != value}
    hire_date = values["hire_date"]
    if records and hire_date > records[0].effective_date:
        message = (
            f"The first salary is from {records[0].effective_date}: change the hire date "
            "in the app, which moves the starting salary with it."
        )
        errors.append(RowError(row.line, "hire_date", message))
    salary = _new_salary(row, employee, hire_date, records, references, errors)
    if errors or (not changed and salary is None):
        return None
    shown = {
        LABELS.get(name, name): (
            references.shown(name, getattr(employee, name)),
            references.shown(name, value),
        )
        for name, value in changed.items()
    }
    return Change(
        row.line, employee.pk, employee.employee_code, row.full_name, changed, shown, salary
    )


def _new_salary(
    row: Row,
    employee: Employee,
    hire_date: date,
    records: list[SalaryRecord],
    references: _References,
    errors: list[RowError],
) -> NewSalary | None:
    """A salary that differs from the one in force on its date adds a record; a matching one
    changes nothing; import never edits or deletes a record (design §6)."""
    if row.salary is None:
        return None
    amount = _amount(row.line, row.salary, references, errors)
    if amount is None:
        return None
    day = row.salary.effective_date
    if day < hire_date:
        errors.append(RowError(row.line, "effective_date", "Before the hire date."))
        return None
    dates = [record.effective_date for record in records]
    in_force = records[bisect_right(dates, day) - 1] if dates and dates[0] <= day else None
    if in_force is not None and (in_force.amount, in_force.currency_id) == (
        amount,
        row.salary.currency,
    ):
        return None
    if in_force is not None and in_force.effective_date == day:
        message = f"There's already a different salary on {day}: correct it in the app."
        errors.append(RowError(row.line, "salary", message))
        return None
    reason = row.salary.reason or (Reason.HIRE if not records else None)
    if reason is None:
        message = (
            "Give the reason for the change: merit, promotion, market, transfer or correction."
        )
        errors.append(RowError(row.line, "reason", message))
        return None
    if reason == Reason.HIRE and records:
        errors.append(RowError(row.line, "reason", "Only the first salary is a hire."))
        return None
    return NewSalary(day, amount, row.salary.currency, reason)
