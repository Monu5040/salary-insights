"""Insights (design §4). What each number means is defined there and in domain.stats.

Every function returns exact decimals; rounding to a currency's decimals happens only when
the answer is written out.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from django.conf import settings

from apps.analytics.sql import Filters, base, explore_query, fetch
from apps.employees.models import Employee
from apps.reference.models import Currency
from domain.fx import MissingRate, Rates
from domain.money import Money
from domain.stats import (
    PeerGroup,
    Range,
    choose_peer_group,
    compa_ratio,
    percentile_rank,
    salary_range,
)


@dataclass(frozen=True)
class Basis:
    """What every number in an answer is relative to: a currency and the filters."""

    today: date
    currency: str
    minor_units: int
    rate: Decimal  # USD per unit of `currency`
    filters: Filters


def basis(today: date, currency: str, filters: Filters) -> Basis:
    """Raises MissingRate for a currency the app doesn't know."""
    found = Currency.objects.filter(code=currency).first()
    if found is None:
        raise MissingRate(currency)
    return Basis(today, currency, found.minor_units, found.usd_per_unit, filters)


@dataclass(frozen=True)
class Group:
    keys: dict[str, str]
    labels: dict[str, str]
    headcount: int
    values: dict[str, Any]


def explore(scope: Basis, metrics: list[str], by: list[str]) -> list[Group]:
    """Metrics for each group of up to two dimensions (design §4 Explorer). With no
    dimensions, one group: everyone in scope."""
    sql, params = base(scope.today, scope.rate, scope.filters)
    groups = []
    for row in fetch(explore_query(sql, metrics, by), params):
        keys = {name: str(row[f"key_{index}"]) for index, name in enumerate(by)}
        labels = {name: str(row[f"label_{index}"]) for index, name in enumerate(by)}
        values = {name: row[f"m_{name}"] for name in metrics}
        groups.append(Group(keys, labels, row["headcount"], values))
    return groups


# Peer groups, narrowest first (design §4): the first with enough people is used.
PEER_GROUPS = [
    ("country", "Same job title and country"),
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


def peer_position(employee: Employee) -> PeerPosition:
    """Where the employee's salary sits among colleagues with the same job title, in the
    currency of the employee's country, converted at the fixed rates. The employee is not
    their own peer."""
    rates = Rates(dict(Currency.objects.values_list("code", "usd_per_unit")))
    currency = employee.country.default_currency
    pay = rates.convert(Money(employee.salary, employee.currency_id), currency.code).amount
    colleagues = (
        Employee.objects.filter(job_title=employee.job_title)
        .exclude(pk=employee.pk)
        .values_list("country_id", "salary", "currency_id")
    )
    peers = [
        (country, rates.convert(Money(salary, paid_in), currency.code).amount)
        for country, salary, paid_in in colleagues
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
