"""Insights (design §4, §7). Read-only."""

from typing import Any

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.analytics import questions, selectors
from apps.analytics.presets import PRESETS
from apps.analytics.serializers import (
    AskSerializer,
    EquityQuery,
    EquitySerializer,
    ExploreQuery,
    ExploreSerializer,
    InsightQuery,
    PresetSerializer,
    QuestionSerializer,
    SummarySerializer,
)
from apps.analytics.sql import Filters
from apps.core import clock
from apps.core.errors import ApiProblem, Unprocessable
from apps.core.pagination import page_of_list
from domain.fx import MissingRate
from domain.money import money_text


class QuestionsUnavailable(ApiProblem):
    """503: the question box has no Groq key, or Groq didn't answer."""

    status_code = 503
    default_code = "questions_unavailable"


def _query(kind: type[InsightQuery], data: Any) -> dict[str, Any]:
    query = kind(data=data)
    query.is_valid(raise_exception=True)
    params: dict[str, Any] = query.validated_data
    return params


def _scope(params: dict[str, Any]) -> selectors.Basis:
    filters = Filters(tuple(params["country"]), tuple(params["department"]))
    currency = params.get("currency") or settings.REPORTING_CURRENCY
    as_of = params.get("as_of") or clock.today()
    try:
        return selectors.basis(as_of, currency, filters)
    except MissingRate as missing:
        raise Unprocessable(str(missing)) from None


def _answer(scope: selectors.Basis) -> dict[str, Any]:
    """The basis every answer states (design §4)."""
    return {
        "as_of": scope.as_of,
        "currency": scope.currency,
        "fx_basis": "Converted through USD at fixed budget exchange rates",
    }


class SummaryView(APIView):
    @extend_schema(parameters=[InsightQuery], responses=SummarySerializer)
    def get(self, request: Request) -> Response:
        """Headcount, payroll and the median and mean salary on a day."""
        scope = _scope(_query(InsightQuery, request.query_params))
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


def _explore(params: dict[str, Any]) -> dict[str, Any]:
    scope = _scope(params)
    groups = selectors.explore(scope, params["metric"], params["by"])

    def written(name: str, value: Any) -> str | None:
        if value is None:
            return None
        return str(value) if name == "headcount" else money_text(value, scope.minor_units)

    return _answer(scope) | {
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


class ExploreView(APIView):
    @extend_schema(parameters=[ExploreQuery], responses=ExploreSerializer)
    def get(self, request: Request) -> Response:
        """Any of the metrics, grouped by up to two things (design §4 Explorer)."""
        answer = _explore(_query(ExploreQuery, request.query_params))
        return Response(ExploreSerializer(answer).data)


class EquityView(APIView):
    @extend_schema(parameters=[EquityQuery], responses=EquitySerializer)
    def get(self, request: Request) -> Response:
        """People paid far from others with the same job title, furthest out first."""
        params = _query(EquityQuery, request.query_params)
        scope = _scope(params)
        count, page = page_of_list(selectors.outliers(scope), params["page"], params["page_size"])
        low, high = settings.PAY_EQUITY_BAND
        answer = _answer(scope) | {
            "band": [str(low), str(high)],
            "count": count,
            "page": params["page"],
            "page_size": params["page_size"],
            "results": [
                {
                    "id": outlier.id,
                    "employee_code": outlier.employee_code,
                    "full_name": outlier.full_name,
                    "country_name": outlier.country_name,
                    "job_title": outlier.job_title,
                    "pay": money_text(outlier.pay, scope.minor_units),
                    "peer_median": money_text(outlier.peer_median, scope.minor_units),
                    "compa_ratio": money_text(outlier.compa_ratio, 2),
                    "definition": outlier.definition,
                    "peers": outlier.peers,
                }
                for outlier in page
            ],
        }
        return Response(EquitySerializer(answer).data)


class QuestionThrottle(AnonRateThrottle):
    """The demo is open, and every question costs a Groq call: a few a minute per address."""

    scope = "questions"


class AskView(APIView):
    throttle_classes = [QuestionThrottle]

    @extend_schema(request=QuestionSerializer, responses=AskSerializer)
    def post(self, request: Request) -> Response:
        """A question in plain English, answered by the explorer (design §4). 422 when it
        can't be turned into an explorer query; 503 when Groq isn't set up or didn't answer."""
        form = QuestionSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        question = form.validated_data["question"]
        try:
            reading = questions.interpret(question, clock.today())
        except questions.NotConfigured as error:
            raise QuestionsUnavailable(str(error)) from None
        except questions.ServiceFailed:
            raise QuestionsUnavailable("The question service didn't answer. Try again.") from None
        if reading.get("understood") is False:
            raise Unprocessable(
                "That question isn't one the explorer can answer. Ask about salaries, payroll "
                "or headcount, by country, department, job title or tenure."
            )
        query = questions.as_query(reading)
        try:
            params = _query(ExploreQuery, query)
        except ValidationError:
            raise Unprocessable(
                "The question couldn't be turned into an explorer query. Try rephrasing it."
            ) from None
        summary = reading.get("summary")
        body = {
            "question": question,
            "summary": summary if isinstance(summary, str) and summary else "Here is the answer.",
            "query": query,
            "answer": _explore(params),
        }
        return Response(AskSerializer(body).data)


class PresetsView(APIView):
    @extend_schema(responses=PresetSerializer(many=True))
    def get(self, request: Request) -> Response:
        """The dashboard's questions, each a saved explorer query (analytics/presets.py)."""
        return Response(PresetSerializer(PRESETS, many=True).data)
