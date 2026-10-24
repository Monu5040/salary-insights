"""Small builders for test data. Currencies, countries and departments come from migrations."""

from datetime import date
from decimal import Decimal
from itertools import count
from typing import Any

from apps.compensation.models import SalaryRecord
from apps.employees.models import Employee
from apps.reference.models import Country, Department
from domain.text import fold

_numbers = count(1)


def department(name: str = "Engineering") -> Department:
    return Department.objects.get_or_create(name=name)[0]


def employee(
    salary: Decimal | str | None = Decimal("1800000"), currency_id: str = "INR", **overrides: Any
) -> Employee:
    """An employee hired on 15 Jan 2024 with a starting salary, unless `salary` is None."""
    number = next(_numbers)
    fields: dict[str, Any] = {
        "employee_code": f"T{number:05d}",
        "full_name": f"Test Person {number}",
        "email": f"person{number}@acme.example",
        "country": Country.objects.get(code="IN"),
        "department": department(),
        "job_title": "Software Engineer",
        "hire_date": date(2024, 1, 15),
    }
    fields.update(overrides)
    fields.setdefault("search_text", fold(f"{fields['full_name']} {fields['employee_code']}"))
    person = Employee.objects.create(**fields)
    if salary is not None:
        record(person, amount=Decimal(salary), currency_id=currency_id)
    return person


def record(of: Employee, **overrides: Any) -> SalaryRecord:
    """A salary record: by default the starting salary on the hire date."""
    fields: dict[str, Any] = {
        "employee": of,
        "effective_date": of.hire_date,
        "amount": Decimal("1800000"),
        "currency_id": "INR",
        "reason": "hire",
    }
    fields.update(overrides)
    return SalaryRecord.objects.create(**fields)
