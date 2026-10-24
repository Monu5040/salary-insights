"""Insights (design §4). What each number means is defined there and in domain.stats.

Every function returns exact decimals; rounding to a currency's decimals happens only when
the answer is written out.
"""

from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from django.conf import settings

from apps.analytics.sql import Filters, base, explore_query, fetch, select
from apps.compensation.selectors import with_salary_on
from apps.employees.models import Employee
from apps.reference.models import Currency
from domain.fx import MissingRate, Rates
from domain.money import Money
from domain.stats import (
    PeerGroup,
    Range,
    choose_peer_group,
    compa_ratio,
    is_outlier,
    percentile_excluding,
    percentile_rank,
    salary_range,
)

_HALF = Decimal("0.5")


@dataclass(frozen=True)
class Basis:
    """What every number in an answer is relative to: a day, a currency and the filters."""

    as_of: date
    currency: str
    minor_units: int
    rate: Decimal  # USD per unit of `currency`
    filters: Filters


def basis(as_of: date, currency: str, filters: Filters) -> Basis:
    """Raises MissingRate for a currency the app doesn't know."""
    found = Currency.objects.filter(code=currency).first()
    if found is None:
        raise MissingRate(currency)
    return Basis(as_of, currency, found.minor_units, found.usd_per_unit, filters)


@dataclass(frozen=True)
class Group:
    keys: dict[str, str]
    labels: dict[str, str]
    headcount: int
    values: dict[str, Any]


def explore(scope: Basis, metrics: list[str], by: list[str]) -> list[Group]:
    """Metrics for each group of up to two dimensions (design §4 Explorer). With no
    dimensions, one group: everyone in scope."""
    sql, params = base(scope.as_of, scope.rate, scope.filters)
    groups = []
    for row in fetch(explore_query(sql, metrics, by), params):
        keys = {name: str(row[f"key_{index}"]) for index, name in enumerate(by)}
        labels = {name: str(row[f"label_{index}"]) for index, name in enumerate(by)}
        values = {name: row[f"m_{name}"] for name in metrics}
        groups.append(Group(keys, labels, row["headcount"], values))
    return groups


# Peer groups, narrowest first (design §4): the first with enough people is used.
PEER_GROUPS = [
    ("country_id", "Same job title and country"),
    (None, "Same job title, every country"),
]


@dataclass(frozen=True)
class PeerPosition:
    currency: str
    minor_units: int
    pay: Decimal  # the employee's, in the country's currency
    definition: str
    range: Range
    percentile_rank: Decimal | None
    compa_ratio: Decimal | None


def peer_position(employee: Employee, today: date) -> PeerPosition | None:
    """Where the employee's salary sits among colleagues with the same job title, in the
    currency of the employee's country, converted at the fixed rates. The employee is not
    their own peer. None before their first salary takes effect.

    `employee` comes from employees.selectors.employees(today), with its salary that day."""
    amount = getattr(employee, "salary_amount", None)
    if amount is None:
        return None
    rates = Rates(dict(Currency.objects.values_list("code", "usd_per_unit")))
    currency = employee.country.default_currency
    paid_in: str = employee.salary_currency  # type: ignore[attr-defined]
    pay = rates.convert(Money(amount, paid_in), currency.code).amount
    colleagues = (
        with_salary_on(Employee.objects.filter(job_title=employee.job_title), today)
        .exclude(pk=employee.pk)
        # with_salary_on adds these; django-stubs can't see annotations made in another function.
        .values_list("country_id", "salary_amount", "salary_currency")  # type: ignore[misc]
    )
    peers = [
        (country, rates.convert(Money(salary, salary_currency), currency.code).amount)
        for country, salary, salary_currency in colleagues
        if salary is not None  # not started yet
    ]
    groups = [
        (
            definition,
            [value for country, value in peers if field is None or country == employee.country_id],
        )
        for field, definition in PEER_GROUPS
    ]
    chosen = choose_peer_group(
        [PeerGroup(definition, len(values)) for definition, values in groups],
        settings.MIN_GROUP_SIZE,
    )
    values = dict(groups)[chosen.definition]
    spread = salary_range(values, settings.MIN_GROUP_SIZE)
    return PeerPosition(
        currency=currency.code,
        minor_units=currency.minor_units,
        pay=pay,
        definition=chosen.definition,
        range=spread,
        percentile_rank=percentile_rank(pay, values),
        compa_ratio=compa_ratio(pay, spread.median),
    )


@dataclass(frozen=True)
class Outlier:
    id: int
    employee_code: str
    full_name: str
    country_name: str
    job_title: str
    pay: Decimal  # in the answer's currency
    peer_median: Decimal
    compa_ratio: Decimal
    definition: str
    peers: int


def outliers(scope: Basis) -> list[Outlier]:
    """Pay equity without gender (requirements): people paid far from others with the same
    job title, a compa-ratio outside PAY_EQUITY_BAND, only where the peer group is big
    enough (design §4). Peers are chosen as on the employee's page and leave the employee
    out, so both screens give the same ratio. Furthest out first."""
    sql, params = base(scope.as_of, scope.rate, scope.filters)
    columns = "id, employee_code, full_name, country_id, country_name, job_title, pay"
    rows = fetch(select(sql, columns), params)

    def key(row: dict[str, Any], field: str | None) -> tuple[Any, ...]:
        return (row["job_title"],) if field is None else (row["job_title"], row[field])

    groups: list[dict[tuple[Any, ...], list[Decimal]]] = []
    for field, _ in PEER_GROUPS:
        members: dict[tuple[Any, ...], list[Decimal]] = defaultdict(list)
        for row in rows:
            members[key(row, field)].append(row["pay"])
        groups.append({group: sorted(values) for group, values in members.items()})

    found = []
    for row in rows:
        pay = row["pay"]
        candidates = [
            (definition, groups[index][key(row, field)])
            for index, (field, definition) in enumerate(PEER_GROUPS)
        ]
        chosen = choose_peer_group(
            [PeerGroup(definition, len(values) - 1) for definition, values in candidates],
            settings.MIN_GROUP_SIZE,
        )
        values = dict(candidates)[chosen.definition]
        median = percentile_excluding(values, bisect_left(values, pay), _HALF)
        ratio = compa_ratio(pay, median)
        if (
            ratio is not None
            and median is not None
            and is_outlier(ratio, settings.PAY_EQUITY_BAND, chosen.size, settings.MIN_GROUP_SIZE)
        ):
            found.append(
                Outlier(
                    row["id"],
                    row["employee_code"],
                    row["full_name"],
                    row["country_name"],
                    row["job_title"],
                    pay,
                    median,
                    ratio,
                    chosen.definition,
                    chosen.size,
                )
            )
    return sorted(found, key=lambda outlier: (-abs(outlier.compa_ratio - 1), outlier.full_name))
