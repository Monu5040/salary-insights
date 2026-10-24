"""Money: exact amounts in a currency's minor units (design D5; edge cases #1, #2, #6, #7, #8).

Amounts are always `Decimal`, never float. A currency's minor units are the digits after the
decimal point: 0 for JPY, 2 for USD and INR, 3 for KWD.
"""

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

# Salaries are stored as NUMERIC(19,4): at most 15 digits before the decimal point.
MAX_INTEGER_DIGITS = 15
_PLAIN_NUMBER = re.compile(r"\d+(\.\d+)?")


class InvalidAmount(ValueError):
    """An amount that can't be stored, or doesn't fit its currency."""


class CurrencyMismatch(ValueError):
    """Amounts in different currencies were combined without converting them first."""


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __add__(self, other: "Money") -> "Money":
        if other.currency != self.currency:
            raise CurrencyMismatch(f"Can't add {other.currency} to {self.currency}; convert first.")
        return Money(self.amount + other.amount, self.currency)


def quantum(minor_units: int) -> Decimal:
    """The currency's smallest step: 1 for JPY, 0.01 for USD, 0.001 for KWD."""
    return Decimal(1).scaleb(-minor_units)


def round_to_minor_unit(amount: Decimal, minor_units: int) -> Decimal:
    """Round half up to the currency's smallest step."""
    return amount.quantize(quantum(minor_units), rounding=ROUND_HALF_UP)


def money_text(amount: Decimal, minor_units: int) -> str:
    """An amount as the API sends it: a string at the currency's precision, such as
    "1926000.00" or "150000" for JPY. Never a float, never exponent notation (design D5)."""
    return format(round_to_minor_unit(amount, minor_units), "f")


def apply_raise(amount: Decimal, percent: Decimal, minor_units: int) -> Decimal:
    """The new amount after a percentage change, rounded half up to the currency's step.

    This is what the change form previews and what the server saves (edge case #6).
    """
    return round_to_minor_unit(amount * (1 + percent / 100), minor_units)


def raise_percent(previous: Decimal, current: Decimal) -> Decimal:
    """The percentage change from previous to current: 7 for +7%."""
    return (current - previous) / previous * 100


def parse_amount(raw: str, minor_units: int, ceiling: Decimal | None = None) -> Decimal:
    """Strictly parse an annual salary typed or imported as text.

    Accepts a plain number only (no separators, symbols or exponents), more than zero,
    with no more decimals than the currency has, and small enough to store. `ceiling` is
    the currency's sanity limit, which catches extra zeros typed by mistake (edge case #7).
    """
    text = raw.strip()
    if not _PLAIN_NUMBER.fullmatch(text):
        raise InvalidAmount(f"Enter a plain number such as 85000.50, not {raw!r}.")
    amount = Decimal(text)
    if amount <= 0:
        raise InvalidAmount("The amount must be more than zero.")
    # Check the size first: rounding a huge number would overflow Decimal's precision.
    if amount >= Decimal(10) ** MAX_INTEGER_DIGITS:
        raise InvalidAmount("The amount is too large to store.")
    if amount != round_to_minor_unit(amount, minor_units):
        raise InvalidAmount(f"This currency allows at most {minor_units} decimal places.")
    if ceiling is not None and amount > ceiling:
        raise InvalidAmount(
            f"{amount} is above {ceiling} for this currency: check for extra zeros."
        )
    return amount
