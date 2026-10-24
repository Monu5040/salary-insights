"""Currency conversion at fixed rates (design §3 and §4; edge case #4).

Each currency has one rate, USD per unit, set as reference data: finance reports at fixed
budget rates, so there is no rate history and no live feed. Converting A to B goes through
USD: amount * usd_per_unit(A) / usd_per_unit(B). Results stay exact; round only for display,
so totals don't accumulate rounding error.
"""

from collections.abc import Mapping
from decimal import Decimal

from domain.money import Money


class MissingRate(LookupError):
    """No rate for a currency. Reported to the user, never treated as zero."""

    def __init__(self, currency: str) -> None:
        super().__init__(f"No exchange rate for {currency}.")
        self.currency = currency


class Rates:
    """USD per unit of each currency."""

    def __init__(self, usd_per_unit: Mapping[str, Decimal]) -> None:
        for currency, rate in usd_per_unit.items():
            if rate <= 0:
                raise ValueError(f"A rate must be positive, got {rate} for {currency}.")
        self._usd_per_unit = dict(usd_per_unit)

    def usd_per_unit(self, currency: str) -> Decimal:
        try:
            return self._usd_per_unit[currency]
        except KeyError:
            raise MissingRate(currency) from None

    def convert(self, money: Money, to_currency: str) -> Money:
        if money.currency == to_currency:
            return money
        usd = money.amount * self.usd_per_unit(money.currency)
        return Money(usd / self.usd_per_unit(to_currency), to_currency)
