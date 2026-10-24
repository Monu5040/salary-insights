"""Query strings and answer shapes for the insights (design §7).

Answers are built as plain data with every amount already written as a string at the
currency's decimals (design D5); these serializers describe them for the API schema.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.analytics.selectors import PeerPosition
from apps.analytics.sql import DIMENSIONS, METRICS
from apps.core.query import StrictQuery
from domain.money import money_text


class InsightQuery(StrictQuery):
    currency = serializers.RegexField(
        r"^[A-Z]{3}$", required=False, help_text="Defaults to the reporting currency"
    )
    country = serializers.ListField(child=serializers.CharField(max_length=2), default=list)
    department = serializers.ListField(child=serializers.IntegerField(), default=list)


class ExploreQuery(InsightQuery):
    metric = serializers.ListField(
        child=serializers.ChoiceField(choices=list(METRICS)), min_length=1, max_length=5
    )
    by = serializers.ListField(
        child=serializers.ChoiceField(choices=list(DIMENSIONS)), max_length=2, default=list
    )

    def validate_by(self, value: list[str]) -> list[str]:
        if len(set(value)) < len(value):
            raise serializers.ValidationError("Group by two different things.")
        return value


class AnswerSerializer(serializers.Serializer[Any]):
    """What every number in an answer is relative to (design §4)."""

    currency = serializers.CharField()
    fx_basis = serializers.CharField()


class SummarySerializer(AnswerSerializer):
    headcount = serializers.IntegerField()
    payroll = serializers.CharField(help_text="Annual salaries, added up")
    median = serializers.CharField(allow_null=True)
    mean = serializers.CharField(allow_null=True)


class GroupSerializer(serializers.Serializer[Any]):
    keys = serializers.DictField(child=serializers.CharField())
    labels = serializers.DictField(child=serializers.CharField())
    headcount = serializers.IntegerField()
    low_sample = serializers.BooleanField(help_text="Fewer than MIN_GROUP_SIZE: read with care")
    values = serializers.DictField(child=serializers.CharField(allow_null=True))


class ExploreSerializer(AnswerSerializer):
    metrics = serializers.ListField(child=serializers.CharField())
    by = serializers.ListField(child=serializers.CharField())
    groups = GroupSerializer(many=True)


class PresetSerializer(serializers.Serializer[Any]):
    id = serializers.CharField()
    title = serializers.CharField()
    chart = serializers.ChoiceField(choices=["bars", "ranges", "table"])
    metrics = serializers.ListField(child=serializers.CharField())
    by = serializers.ListField(child=serializers.CharField())


def _money(amount: Decimal | None, minor_units: int) -> str | None:
    return None if amount is None else money_text(amount, minor_units)


def _fixed(value: Decimal | None, places: str) -> str | None:
    return None if value is None else format(value.quantize(Decimal(places), ROUND_HALF_UP), "f")


class PeerPositionSerializer(serializers.Serializer[PeerPosition]):
    """The employee's salary against the chosen peer group, in their country's currency."""

    currency = serializers.CharField()
    definition = serializers.CharField(help_text="Which peer group was used")
    peers = serializers.IntegerField(source="range.n")
    low_sample = serializers.BooleanField(source="range.low_sample")
    pay = serializers.SerializerMethodField()
    p10 = serializers.SerializerMethodField()
    p25 = serializers.SerializerMethodField()
    median = serializers.SerializerMethodField()
    p75 = serializers.SerializerMethodField()
    p90 = serializers.SerializerMethodField()
    percentile_rank = serializers.SerializerMethodField(help_text="Share of peers paid less, 0-100")
    compa_ratio = serializers.SerializerMethodField(help_text="Pay divided by the peer median")

    def get_pay(self, position: PeerPosition) -> str:
        return money_text(position.pay, position.minor_units)

    def get_p10(self, position: PeerPosition) -> str | None:
        return _money(position.range.p10, position.minor_units)

    def get_p25(self, position: PeerPosition) -> str | None:
        return _money(position.range.p25, position.minor_units)

    def get_median(self, position: PeerPosition) -> str | None:
        return _money(position.range.median, position.minor_units)

    def get_p75(self, position: PeerPosition) -> str | None:
        return _money(position.range.p75, position.minor_units)

    def get_p90(self, position: PeerPosition) -> str | None:
        return _money(position.range.p90, position.minor_units)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_percentile_rank(self, position: PeerPosition) -> str | None:
        return _fixed(position.percentile_rank, "1")

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_compa_ratio(self, position: PeerPosition) -> str | None:
        return _fixed(position.compa_ratio, "0.01")
