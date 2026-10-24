"""Statistics behind the insights (design §4). Pure functions on exact decimals.

Group-size thresholds and the pay-equity band are passed in by the caller from settings
(design §2 Configuration), so this package never reads Django settings.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from domain.money import raise_percent

PERCENTILES = (Decimal("0.10"), Decimal("0.25"), Decimal("0.50"), Decimal("0.75"), Decimal("0.90"))


def percentile(values: Sequence[Decimal], fraction: Decimal) -> Decimal | None:
    """Linear interpolation between closest ranks, the same as PostgreSQL's percentile_cont."""
    if not 0 <= fraction <= 1:
        raise ValueError(f"The fraction must be between 0 and 1, got {fraction}.")
    if not values:
        return None
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def median(values: Sequence[Decimal]) -> Decimal | None:
    return percentile(values, Decimal("0.5"))


def percentile_excluding(
    ordered: Sequence[Decimal], skip: int, fraction: Decimal
) -> Decimal | None:
    """The percentile of `ordered` (sorted) without the value at index `skip`.

    The same as percentile() on the list with that value removed, without copying it, so
    every employee in a group of n is compared with their peers in O(1) after one sort.
    """
    size = len(ordered) - 1
    if size <= 0:
        return None

    def at(index: int) -> Decimal:
        return ordered[index] if index < skip else ordered[index + 1]

    position = fraction * (size - 1)
    lower = int(position)
    upper = min(lower + 1, size - 1)
    return at(lower) + (at(upper) - at(lower)) * (position - lower)


@dataclass(frozen=True)
class Range:
    n: int
    p10: Decimal | None
    p25: Decimal | None
    median: Decimal | None
    p75: Decimal | None
    p90: Decimal | None
    low_sample: bool


def salary_range(values: Sequence[Decimal], min_group_size: int) -> Range:
    """P10 to P90 of a group. Groups smaller than the minimum are flagged, not hidden."""
    p10, p25, p50, p75, p90 = (percentile(values, fraction) for fraction in PERCENTILES)
    return Range(len(values), p10, p25, p50, p75, p90, low_sample=len(values) < min_group_size)


def percentile_rank(value: Decimal, peers: Sequence[Decimal]) -> Decimal | None:
    """The share of peers paid less, as 0 to 100, with ties counting half.

    `peers` excludes the employee being ranked.
    """
    if not peers:
        return None
    below = sum(1 for peer in peers if peer < value)
    equal = sum(1 for peer in peers if peer == value)
    return (below + Decimal(equal) / 2) / len(peers) * 100


def compa_ratio(salary: Decimal, peer_median: Decimal | None) -> Decimal | None:
    """Salary divided by the peer median: 1.0 means paid exactly the median."""
    if not peer_median:
        return None
    return salary / peer_median


def is_outlier(
    ratio: Decimal | None, band: tuple[Decimal, Decimal], peer_count: int, min_group_size: int
) -> bool:
    """Outside the band (edges count as inside), and only when the peer group is big enough."""
    if ratio is None or peer_count < min_group_size:
        return False
    low, high = band
    return not low <= ratio <= high


@dataclass(frozen=True)
class PeerGroup:
    definition: str
    size: int


def choose_peer_group(candidates: Sequence[PeerGroup], min_group_size: int) -> PeerGroup:
    """The narrowest definition with enough people, else the broadest (edge case #24).

    Candidates run from narrowest to broadest; the caller reports which one was used.
    """
    if not candidates:
        raise ValueError("Give at least one peer group definition.")
    return next((group for group in candidates if group.size >= min_group_size), candidates[-1])


class Reason(StrEnum):
    HIRE = "hire"
    MERIT = "merit"
    PROMOTION = "promotion"
    MARKET = "market"
    TRANSFER = "transfer"
    CORRECTION = "correction"


NOT_RAISES = frozenset({Reason.HIRE, Reason.CORRECTION})


@dataclass(frozen=True)
class SalaryChange:
    effective_date: date
    amount: Decimal
    currency: str
    reason: Reason


def is_currency_change(previous: SalaryChange, current: SalaryChange) -> bool:
    return previous.currency != current.currency


def raise_percent_between(previous: SalaryChange | None, current: SalaryChange) -> Decimal | None:
    """The raise % of a change against the record before it (design §4 Raise %).

    None when it isn't a raise: the first record, hire and correction records, and currency
    changes (transfers), which the caller counts separately (edge case #7).
    """
    if previous is None or current.reason in NOT_RAISES or is_currency_change(previous, current):
        return None
    return raise_percent(previous.amount, current.amount)
