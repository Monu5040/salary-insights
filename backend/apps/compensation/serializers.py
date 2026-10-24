from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from rest_framework import serializers

from apps.compensation.models import SalaryRecord
from apps.compensation.selectors import HistoryRow
from apps.employees.serializers import AmountField
from apps.reference.models import Currency
from domain.money import InvalidAmount, money_text, parse_amount
from domain.stats import Reason


class SalaryChangeSerializer(serializers.Serializer[Any]):
    """A change as the form sends it: always the absolute amount, never a % (design §6)."""

    effective_date = serializers.DateField()
    amount = AmountField(max_length=40)
    currency = serializers.SlugRelatedField(slug_field="code", queryset=Currency.objects.all())
    reason = serializers.ChoiceField(choices=[reason.value for reason in Reason])
    note = serializers.CharField(max_length=500, allow_blank=True, required=False, default="")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """The amount must fit its currency: its decimals and its typo ceiling (#2, #7).

        A correction may send only one of the two, so the other comes from the record."""
        if "amount" not in attrs and "currency" not in attrs:
            return attrs
        entry = self.instance if isinstance(self.instance, SalaryRecord) else None
        currency: Currency = attrs.get("currency") or entry.currency  # type: ignore[union-attr]
        raw = attrs.get("amount")
        if raw is None:
            raw = money_text(entry.amount, entry.currency.minor_units)  # type: ignore[union-attr]
        try:
            attrs["amount"] = parse_amount(raw, currency.minor_units, currency.salary_ceiling)
        except InvalidAmount as error:
            raise serializers.ValidationError({"amount": [str(error)]}) from None
        return attrs


class SalaryRowSerializer(serializers.Serializer[HistoryRow]):
    id = serializers.IntegerField(source="record.pk")
    effective_date = serializers.DateField(source="record.effective_date")
    amount = serializers.SerializerMethodField()
    currency = serializers.CharField(source="record.currency_id")
    reason = serializers.CharField(source="record.reason")
    note = serializers.CharField(source="record.note")
    raise_percent = serializers.SerializerMethodField(
        help_text="Against the change before, in the same currency; null when not a raise"
    )
    currency_change = serializers.BooleanField()
    scheduled = serializers.BooleanField(help_text="Takes effect after today")

    def get_amount(self, row: HistoryRow) -> str:
        return money_text(row.record.amount, row.record.currency.minor_units)

    def get_raise_percent(self, row: HistoryRow) -> str | None:
        if row.raise_percent is None:
            return None
        return format(row.raise_percent.quantize(Decimal("0.01"), ROUND_HALF_UP), "f")


class SalaryHistorySerializer(serializers.Serializer[Any]):
    """An employee's salary history, newest first, with the version for the next If-Match."""

    employee_version = serializers.IntegerField()
    current_id = serializers.IntegerField(allow_null=True, help_text="The change in force today")
    records = SalaryRowSerializer(many=True)
