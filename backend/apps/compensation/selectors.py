"""Reading salaries: an employee's history, and the salary in force on a date (design D4, §4).

The salary on a date is the latest record dated on or before it.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import OuterRef, QuerySet, Subquery

from apps.compensation.models import SalaryRecord
from apps.employees.models import Employee
from domain.stats import Reason, SalaryChange, is_currency_change, raise_percent_between


def with_salary_on(rows: QuerySet[Employee], day: date) -> QuerySet[Employee]:
    """Each employee with the amount, currency and its decimals in force on `day`: one
    subquery per column over the unique (employee, effective_date) index."""
    in_force = SalaryRecord.objects.filter(
        employee=OuterRef("pk"), effective_date__lte=day
    ).order_by("-effective_date")
    return rows.annotate(
        salary_amount=Subquery(in_force.values("amount")[:1]),
        salary_currency=Subquery(in_force.values("currency")[:1]),
        salary_minor_units=Subquery(in_force.values("currency__minor_units")[:1]),
    )


@dataclass(frozen=True)
class HistoryRow:
    record: SalaryRecord
    raise_percent: Decimal | None  # against the record before, in the same currency
    currency_change: bool  # a transfer: not a raise
    scheduled: bool  # takes effect after `today`


def salary_history(employee: Employee, today: date) -> tuple[list[HistoryRow], SalaryRecord | None]:
    """Every record, newest first, and the one in force today.

    Raises are worked out on read, so a back-dated change re-orders the history and both
    neighbours get the right raise % with no stored value to fix.
    """
    records = employee.salary_records.select_related("currency").order_by("effective_date")
    rows: list[HistoryRow] = []
    previous: SalaryChange | None = None
    for record in records:
        change = SalaryChange(
            record.effective_date, record.amount, record.currency_id, Reason(record.reason)
        )
        rows.append(
            HistoryRow(
                record,
                raise_percent_between(previous, change),
                previous is not None and is_currency_change(previous, change),
                record.effective_date > today,
            )
        )
        previous = change
    current = next((row.record for row in reversed(rows) if not row.scheduled), None)
    return rows[::-1], current
