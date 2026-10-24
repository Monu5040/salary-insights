"""Currency conversion at fixed rates (design §3 and §4; edge case #4)."""

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from domain.fx import MissingRate, Rates
from domain.money import Money, round_to_minor_unit

RATES = Rates({"USD": Decimal("1"), "INR": Decimal("0.012"), "JPY": Decimal("0.0067")})


def test_an_unknown_currency_has_no_rate() -> None:
    with pytest.raises(MissingRate, match="No exchange rate for EUR"):
        RATES.usd_per_unit("EUR")


def test_converts_to_usd() -> None:
    salary = Money(Decimal("1800000"), "INR")
    assert RATES.convert(salary, "USD") == Money(Decimal("21600"), "USD")


def test_converts_between_two_currencies_through_usd() -> None:
    converted = RATES.convert(Money(Decimal("5000000"), "JPY"), "INR")
    assert converted.currency == "INR"
    assert round_to_minor_unit(converted.amount, 2) == Decimal("2791666.67")


def test_converting_to_the_same_currency_needs_no_rate() -> None:
    salary = Money(Decimal("90000"), "EUR")
    assert RATES.convert(salary, "EUR") is salary


def test_a_missing_target_rate_is_an_error_not_zero() -> None:
    with pytest.raises(MissingRate) as error:
        RATES.convert(Money(Decimal("100"), "INR"), "EUR")
    assert error.value.currency == "EUR"


@pytest.mark.parametrize("value", ["0", "-0.5"])
def test_a_rate_must_be_positive(value: str) -> None:
    with pytest.raises(ValueError, match="positive"):
        Rates({"INR": Decimal(value)})


rates = st.decimals(min_value=Decimal("0.000001"), max_value=Decimal("1000"), places=6)
amounts = st.decimals(min_value=Decimal("0.01"), max_value=Decimal("999999999999.99"), places=2)


@given(amounts, rates, rates)
def test_converting_there_and_back_returns_the_original_amount(
    amount: Decimal, rate_a: Decimal, rate_b: Decimal
) -> None:
    table = Rates({"AAA": rate_a, "BBB": rate_b})

    there = table.convert(Money(amount, "AAA"), "BBB")
    back = table.convert(there, "AAA")

    assert round_to_minor_unit(back.amount, 2) == amount
