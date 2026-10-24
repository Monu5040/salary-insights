"""manage.py seed (design §12; edge case #30)."""

from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.db import connection
from pytest_django.fixtures import Settings

from apps.compensation.models import SalaryRecord
from apps.employees.models import Employee
from domain.text import fold

pytestmark = pytest.mark.django_db


def seed(**options: object) -> None:
    call_command("seed", stdout=StringIO(), **options)


def test_loads_employees_with_their_salary_history() -> None:
    seed(employees=120, seed=3)

    assert Employee.objects.count() == 120
    assert SalaryRecord.objects.count() > 120
    person = Employee.objects.get(employee_code="E00001")
    assert person.search_text == fold(f"{person.full_name} E00001")
    first = person.salary_records.order_by("effective_date").first()
    assert first is not None and (first.reason, first.effective_date) == ("hire", person.hire_date)


def test_reset_replaces_the_demo_data() -> None:
    # Two runs share this test's transaction. In real use each run commits on its own, so check
    # the deferred foreign keys per statement here: TRUNCATE refuses pending trigger events.
    with connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    seed(employees=50, seed=3)
    seed(employees=80, seed=4, reset=True)

    assert Employee.objects.count() == 80
    assert Employee.objects.order_by("id").values_list("employee_code", flat=True)[0] == "E00001"


def test_refuses_to_replace_data_without_reset() -> None:
    seed(employees=10)
    with pytest.raises(CommandError, match="--reset"):
        seed(employees=10)


@pytest.mark.parametrize("environment", ["production", "unknown", "staging"])
def test_refuses_to_run_outside_dev_test_and_demo(settings: Settings, environment: str) -> None:
    settings.ENVIRONMENT = environment
    with pytest.raises(CommandError, match="runs only in demo, dev, test"):
        seed(employees=5)
    assert not Employee.objects.exists()


def test_runs_on_the_public_demo(settings: Settings) -> None:
    settings.ENVIRONMENT = "demo"
    seed(employees=5)
    assert Employee.objects.count() == 5
