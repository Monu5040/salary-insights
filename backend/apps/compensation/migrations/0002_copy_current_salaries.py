"""Each employee's current salary becomes their starting record, dated on their hire date.

The salary columns on employees stay until the next release (expand now, contract later), so
rolling back to the release before this one still finds its data.
"""

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def copy(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Employee = apps.get_model("employees", "Employee")
    SalaryRecord = apps.get_model("compensation", "SalaryRecord")
    rows = Employee.objects.filter(salary__isnull=False).values_list(
        "pk", "hire_date", "salary", "currency_id"
    )
    SalaryRecord.objects.bulk_create(
        (
            SalaryRecord(
                employee_id=pk,
                effective_date=hired,
                amount=amount,
                currency_id=currency,
                reason="hire",
            )
            for pk, hired, amount, currency in rows.iterator(chunk_size=2000)
        ),
        batch_size=2000,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("compensation", "0001_initial"),
        ("employees", "0002_salary_moves_to_history"),
    ]
    operations = [migrations.RunPython(copy, migrations.RunPython.noop)]
