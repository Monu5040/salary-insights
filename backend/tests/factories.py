"""Small builders for test data. Currencies, countries and departments come from migrations."""

from datetime import date
from decimal import Decimal
from itertools import count
from typing import Any

from apps.employees.models import Employee
from apps.reference.models import Country, Department
from domain.text import fold

_numbers = count(1)


def department(name: str = "Engineering") -> Department:
    return Department.objects.get_or_create(name=name)[0]


def employee(**overrides: Any) -> Employee:
    number = next(_numbers)
    fields: dict[str, Any] = {
        "employee_code": f"T{number:05d}",
        "full_name": f"Test Person {number}",
        "email": f"person{number}@acme.example",
        "country": Country.objects.get(code="IN"),
        "department": department(),
        "job_title": "Software Engineer",
        "hire_date": date(2024, 1, 15),
        "salary": Decimal("1800000"),
        "currency_id": "INR",
    }
    fields.update(overrides)
    fields.setdefault("search_text", fold(f"{fields['full_name']} {fields['employee_code']}"))
    return Employee.objects.create(**fields)
