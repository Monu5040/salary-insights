"""Reading employees: the directory and single records (design §7; edge cases #18 to #21)."""

from collections.abc import Iterator, Sequence
from datetime import date

from django.db.models import OuterRef, QuerySet, Subquery

from apps.compensation.models import SalaryRecord
from apps.compensation.selectors import with_salary_on
from apps.employees.models import Employee
from domain.money import money_text
from domain.text import fold

# The directory's sort keys, the only ones accepted (edge case #21). Each sort ends with id,
# so equal values can't swap places between pages (edge case #19).
SORTS = {
    "employee_code": "employee_code",
    "full_name": "full_name",
    "country": "country__name",
    "department": "department__name",
    "job_title": "job_title",
    "hire_date": "hire_date",
}


def employees(today: date) -> QuerySet[Employee]:
    """Employees with their references and the salary in force today."""
    return with_salary_on(Employee.objects.select_related("country", "department"), today)


def directory(
    *,
    today: date,
    search: str = "",
    countries: Sequence[str] = (),
    departments: Sequence[int] = (),
    sort: str = "full_name",
) -> QuerySet[Employee]:
    """Employees matching the filters, sorted."""
    rows = employees(today)
    if term := fold(search):
        # `contains` on the folded column, which the trigram index serves; Django escapes
        # %, _ and \ in the term, so they match literally (edge case #20).
        rows = rows.filter(search_text__contains=term)
    if countries:
        rows = rows.filter(country_id__in=countries)
    if departments:
        rows = rows.filter(department_id__in=departments)
    descending = sort.startswith("-")
    field = SORTS[sort.removeprefix("-")]
    return rows.order_by(f"-{field}" if descending else field, "id")


# The export's columns are the import's, so an exported sheet imports back unchanged
# (edge case #48).
EXPORT_COLUMNS = [
    "employee_code",
    "full_name",
    "email",
    "country",
    "department",
    "job_title",
    "hire_date",
    "salary",
    "currency",
    "effective_date",
]


def export_table(rows: QuerySet[Employee], today: date) -> Iterator[list[object]]:
    """The directory's rows with the salary in force today, streamed from a server-side
    cursor in constant memory (design §6)."""
    in_force = SalaryRecord.objects.filter(
        employee=OuterRef("pk"), effective_date__lte=today
    ).order_by("-effective_date")
    table = rows.annotate(since=Subquery(in_force.values("effective_date")[:1])).values_list(
        "employee_code",
        "full_name",
        "email",
        "country_id",
        "department__name",
        "job_title",
        "hire_date",
        "salary_amount",
        "salary_currency",
        "since",
        "salary_minor_units",
    )
    for *values, minor_units in table.iterator(chunk_size=2000):
        if values[7] is not None:
            values[7] = money_text(values[7], minor_units)
        yield values
