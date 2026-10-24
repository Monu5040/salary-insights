"""Money: exact amounts in a currency's minor units (design D5; edge cases #1, #2, #6, #7, #8)."""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from domain.money import (
    CurrencyMismatch,
    InvalidAmount,
    Money,
    apply_raise,
    parse_amount,
    quantum,
    raise_percent,
    round_to_minor_unit,
)

VECTORS: dict[str, Any] = json.loads(
    (Path(__file__).parents[4] / "shared" / "money-vectors.json").read_text()
)

amounts = st.decimals(
    min_value=Decimal("0.0001"),
    max_value=Decimal("999999999999999.9999"),
    places=4,
    allow_nan=False,
    allow_infinity=False,
)
minor_units = st.sampled_from([0, 2, 3])


@pytest.mark.parametrize(("minor", "step"), [(0, "1"), (2, "0.01"), (3, "0.001")])
def test_quantum_is_the_currencys_smallest_step(minor: int, step: str) -> None:
    assert quantum(minor) == Decimal(step)


@pytest.mark.parametrize("case", VECTORS["round_to_minor_unit"])
def test_rounding_matches_the_shared_vectors(case: dict[str, Any]) -> None:
    rounded = round_to_minor_unit(Decimal(case["amount"]), case["minor_units"])
    assert str(rounded) == case["expected"]


@pytest.mark.parametrize("case", VECTORS["apply_raise"])
def test_a_percentage_raise_matches_the_shared_vectors(case: dict[str, Any]) -> None:
    new_amount = apply_raise(Decimal(case["amount"]), Decimal(case["percent"]), case["minor_units"])
    assert str(new_amount) == case["expected"]


@given(amounts, minor_units)
def test_rounding_lands_on_the_currencys_step_and_moves_at_most_half_a_step(
    amount: Decimal, minor: int
) -> None:
    rounded = round_to_minor_unit(amount, minor)
    assert rounded == round_to_minor_unit(rounded, minor)
    assert abs(rounded - amount) <= quantum(minor) / 2


@given(amounts, minor_units)
def test_a_zero_raise_only_rounds(amount: Decimal, minor: int) -> None:
    assert apply_raise(amount, Decimal(0), minor) == round_to_minor_unit(amount, minor)


def test_raise_percent_is_the_change_against_the_previous_amount() -> None:
    assert raise_percent(Decimal("1800000"), Decimal("1926000")) == Decimal(7)
    assert raise_percent(Decimal("85000"), Decimal("80750")) == Decimal(-5)


class TestParseAmount:
    def test_accepts_a_plain_number(self) -> None:
        assert parse_amount("85000.50", minor_units=2) == Decimal("85000.50")

    def test_accepts_trailing_zeros_beyond_the_minor_unit(self) -> None:
        assert parse_amount("5000000.00", minor_units=0) == Decimal("5000000")

    @pytest.mark.parametrize("raw", ["85,000", "$85000", "1e5", "85000.", ".5", "", "abc"])
    def test_rejects_anything_but_a_plain_number(self, raw: str) -> None:
        with pytest.raises(InvalidAmount, match="plain number"):
            parse_amount(raw, minor_units=2)

    @pytest.mark.parametrize(("raw", "minor"), [("85000.505", 2), ("5000000.5", 0), ("1.0001", 3)])
    def test_rejects_more_decimals_than_the_currency_has(self, raw: str, minor: int) -> None:
        with pytest.raises(InvalidAmount, match="decimal places"):
            parse_amount(raw, minor_units=minor)

    @pytest.mark.parametrize("raw", ["0", "0.00"])
    def test_rejects_zero(self, raw: str) -> None:
        with pytest.raises(InvalidAmount, match="more than zero"):
            parse_amount(raw, minor_units=2)

    @pytest.mark.parametrize("raw", ["1000000000000000", "1" + "0" * 40 + ".5"])
    def test_rejects_amounts_the_database_cannot_hold(self, raw: str) -> None:
        with pytest.raises(InvalidAmount, match="too large"):
            parse_amount(raw, minor_units=2)

    def test_holds_huge_nominal_amounts(self) -> None:
        assert parse_amount("999999999999999", minor_units=0) == Decimal("999999999999999")

    def test_rejects_amounts_above_the_currency_ceiling(self) -> None:
        with pytest.raises(InvalidAmount, match="extra zeros"):
            parse_amount("85000000", minor_units=2, ceiling=Decimal("10000000"))


class TestMoney:
    def test_adds_amounts_in_the_same_currency(self) -> None:
        total = Money(Decimal("100.10"), "USD") + Money(Decimal("0.90"), "USD")
        assert total == Money(Decimal("101.00"), "USD")

    def test_refuses_to_add_different_currencies(self) -> None:
        with pytest.raises(CurrencyMismatch, match="convert first"):
            _ = Money(Decimal(1), "USD") + Money(Decimal(1), "INR")
