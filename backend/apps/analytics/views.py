"""Insights (design §4, §7). Read-only."""

from typing import Any

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics import selectors
from apps.analytics.presets import PRESETS
from apps.analytics.serializers import (
    ExploreQuery,
    ExploreSerializer,
    InsightQuery,
    PresetSerializer,
    SummarySerializer,
)
from apps.analytics.sql import Filters
from apps.core import clock
from apps.core.errors import Unprocessable
from domain.fx import MissingRate
from domain.money import money_text


def _query(kind: type[InsightQuery], request: Request) -> dict[str, Any]:
    query = kind(data=request.query_params)
    query.is_valid(raise_exception=True)
    data: dict[str, Any] = query.validated_data
    return data


def _scope(params: dict[str, Any]) -> selectors.Basis:
    filters = Filters(tuple(params["country"]), tuple(params["department"]))
    currency = params.get("currency") or settings.REPORTING_CURRENCY
    try:
        return selectors.basis(clock.today(), currency, filters)
    except MissingRate as missing:
        raise Unprocessable(str(missing)) from None


def _answer(scope: selectors.Basis) -> dict[str, Any]:
    """The basis every answer states (design §4)."""
    return {
        "currency": scope.currency,
        "fx_basis": "Converted through USD at fixed budget exchange rates",
    }


class SummaryView(APIView):
    @extend_schema(parameters=[InsightQuery], responses=SummarySerializer)
    def get(self, request: Request) -> Response:
        """Headcount, payroll and the median and mean salary."""
        scope = _scope(_query(InsightQuery, request))
        (everyone,) = selectors.explore(scope, ["payroll", "median", "mean"], [])

        def money(name: str) -> str | None:
            value = everyone.values[name]
            return None if value is None else money_text(value, scope.minor_units)

        answer = _answer(scope) | {
            "headcount": everyone.headcount,
            "payroll": money("payroll"),
            "median": money("median"),
            "mean": money("mean"),
        }
        return Response(SummarySerializer(answer).data)


class ExploreView(APIView):
    @extend_schema(parameters=[ExploreQuery], responses=ExploreSerializer)
    def get(self, request: Request) -> Response:
        """Any of the metrics, grouped by up to two things (design §4 Explorer)."""
        params = _query(ExploreQuery, request)
        scope = _scope(params)
        groups = selectors.explore(scope, params["metric"], params["by"])

        def written(name: str, value: Any) -> str | None:
            if value is None:
                return None
            return str(value) if name == "headcount" else money_text(value, scope.minor_units)

        answer = _answer(scope) | {
            "metrics": params["metric"],
            "by": params["by"],
            "groups": [
                {
                    "keys": group.keys,
                    "labels": group.labels,
                    "headcount": group.headcount,
                    "low_sample": group.headcount < settings.MIN_GROUP_SIZE,
                    "values": {name: written(name, value) for name, value in group.values.items()},
                }
                for group in groups
            ],
        }
        return Response(ExploreSerializer(answer).data)


class PresetsView(APIView):
    @extend_schema(responses=PresetSerializer(many=True))
    def get(self, request: Request) -> Response:
        """The dashboard's questions, each a saved explorer query (analytics/presets.py)."""
        return Response(PresetSerializer(PRESETS, many=True).data)
