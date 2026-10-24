"""Reading employees: the directory and single records (design §7; edge cases #18 to #21)."""

from collections.abc import Sequence

from django.db.models import QuerySet

from apps.employees.models import Employee
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


def employees() -> QuerySet[Employee]:
    return Employee.objects.select_related("country", "department", "currency")


def directory(
    *,
    search: str = "",
    countries: Sequence[str] = (),
    departments: Sequence[int] = (),
    sort: str = "full_name",
) -> QuerySet[Employee]:
    """Employees matching the filters, sorted."""
    rows = employees()
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
