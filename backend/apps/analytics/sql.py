"""The query every insight builds on (design §3), and the pieces the explorer may combine.

Each employee with their salary converted into the chosen currency at the fixed rates.
Values are always bound parameters; SQL text is only ever put together from the constants
in this module (CLAUDE.md, SQL).
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from django.db import connection


@dataclass(frozen=True)
class Filters:
    countries: tuple[str, ...] = ()
    departments: tuple[int, ...] = ()


_BASE = """
WITH base AS (
    SELECT e.id, e.country_id, c.name AS country_name,
           e.department_id, d.name AS department_name,
           e.job_title, e.hire_date,
           e.salary * cur.usd_per_unit / %(target_rate)s AS pay
    FROM employees e
    JOIN countries c ON c.code = e.country_id
    JOIN departments d ON d.id = e.department_id
    JOIN currencies cur ON cur.code = e.currency_id
    WHERE TRUE
      {filters}
)
"""


def base(today: date, target_rate: Decimal, filters: Filters) -> tuple[str, dict[str, Any]]:
    """The `base` CTE, ready for a SELECT to be appended, and its parameters."""
    clauses: list[str] = []
    params: dict[str, Any] = {"today": today, "target_rate": target_rate}
    if filters.countries:
        clauses.append("AND e.country_id = ANY(%(countries)s)")
        params["countries"] = list(filters.countries)
    if filters.departments:
        clauses.append("AND e.department_id = ANY(%(departments)s)")
        params["departments"] = list(filters.departments)
    return _BASE.format(filters="\n      ".join(clauses)), params


@dataclass(frozen=True)
class Dimension:
    key: str  # what the group is
    label: str  # how it is named on screen
    order: str  # how the groups are sorted


_YEARS = "date_part('year', age(%(today)s::date, hire_date))"
_TENURE = (
    f"CASE WHEN {_YEARS} < 1 THEN 'Under 1 year' WHEN {_YEARS} < 3 THEN '1 to 2 years' "
    f"WHEN {_YEARS} < 5 THEN '3 to 4 years' WHEN {_YEARS} < 10 THEN '5 to 9 years' "
    "ELSE '10 years or more' END"
)
_TENURE_ORDER = (
    f"CASE WHEN {_YEARS} < 1 THEN 0 WHEN {_YEARS} < 3 THEN 1 WHEN {_YEARS} < 5 THEN 2 "
    f"WHEN {_YEARS} < 10 THEN 3 ELSE 4 END"
)

# What the explorer can group by (design §4 Explorer); nothing else reaches the SQL.
DIMENSIONS = {
    "country": Dimension("country_id", "country_name", "country_name"),
    "department": Dimension("department_id::text", "department_name", "department_name"),
    "title": Dimension("job_title", "job_title", "job_title"),
    "tenure": Dimension(_TENURE, _TENURE, _TENURE_ORDER),
}


def _percentile(fraction: str) -> str:
    # percentile_cont works in double precision: cast back to numeric (design D5).
    return f"percentile_cont({fraction}) WITHIN GROUP (ORDER BY pay)::numeric"


# What the explorer can measure.
METRICS = {
    "headcount": "count(*)",
    "payroll": "coalesce(sum(pay), 0)",
    "mean": "avg(pay)",
    "median": _percentile("0.5"),
    "p10": _percentile("0.1"),
    "p25": _percentile("0.25"),
    "p75": _percentile("0.75"),
    "p90": _percentile("0.9"),
    "min": "min(pay)",
    "max": "max(pay)",
}


def select(base_sql: str, columns: str, rest: str = "") -> str:
    """A SELECT on `base`. Only this module's constants and literal SQL from the selectors
    are joined here; every value travels as a bound parameter."""
    return f"{base_sql}SELECT {columns} FROM base {rest}"  # noqa: S608 (constants only)


def explore_query(base_sql: str, metrics: list[str], by: list[str]) -> str:
    """Metrics per group of up to two dimensions, both from the allow-lists above."""
    columns: list[str] = []
    for index, name in enumerate(by):
        dimension = DIMENSIONS[name]
        columns += [
            f"{dimension.key} AS key_{index}",
            f"{dimension.label} AS label_{index}",
            f"{dimension.order} AS order_{index}",
        ]
    measures = [f"{METRICS[name]} AS m_{name}" for name in metrics]
    everything = ", ".join([*columns, "count(*) AS headcount", *measures])
    if not by:
        return select(base_sql, everything)
    positions = ", ".join(str(position) for position in range(1, len(columns) + 1))
    order = ", ".join(f"order_{index}, key_{index}" for index in range(len(by)))
    return select(base_sql, everything, f"GROUP BY {positions} ORDER BY {order}")


def fetch(sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        columns = [column.name for column in cursor.description or []]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
