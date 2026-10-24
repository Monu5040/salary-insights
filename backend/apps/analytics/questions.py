"""Natural-language questions (design §4): Groq turns a question into explorer parameters.

The model only ever picks from the explorer's allow-lists, and its answer is validated by the
same query serializer as the explorer's own URL, so a question can't reach the SQL. Only the
question and the reference lists are sent; no salary data leaves the server.
"""

import json
import urllib.error
import urllib.request
from datetime import date
from typing import Any

from django.conf import settings

from apps.analytics.sql import DIMENSIONS, METRICS
from apps.reference.models import Country, Currency, Department

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class NotConfigured(RuntimeError):
    """No GROQ_API_KEY: the rest of the app works, the question box says so."""


class ServiceFailed(RuntimeError):
    """Groq didn't answer, or answered with something that isn't JSON."""


def _instructions(today: date) -> str:
    countries = ", ".join(
        f"{code}={name}" for code, name in Country.objects.values_list("code", "name")
    )
    departments = ", ".join(
        f"{pk}={name}" for pk, name in Department.objects.values_list("pk", "name")
    )
    currencies = ", ".join(Currency.objects.values_list("code", flat=True))
    return (
        "You turn an HR manager's question about salaries into parameters for a fixed query "
        "tool. Reply with one JSON object and nothing else, with these keys:\n"
        f'"metric": 1 to 5 of [{", ".join(METRICS)}]. "payroll" is the sum of annual salaries; '
        '"headcount" counts people.\n'
        f'"by": 0 to 2 different of [{", ".join(DIMENSIONS)}]. "title" is the job title.\n'
        f'"country": a list of country codes, from: {countries}.\n'
        f'"department": a list of department ids (numbers), from: {departments}.\n'
        f'"currency": one of {currencies}, or null for the default.\n'
        f'"as_of": a date YYYY-MM-DD, or null for today ({today.isoformat()}).\n'
        '"summary": one short plain sentence saying what will be shown.\n'
        '"understood": false when the question is not about salaries, headcount or payroll '
        "of these employees, or can't be answered with these parameters.\n"
        "Use empty lists for no filter. Never invent codes or ids."
    )


def _chat(system: str, question: str) -> str:
    """One chat completion from Groq's OpenAI-compatible API, in JSON mode."""
    body = json.dumps(
        {
            "model": settings.GROQ_MODEL,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": question},
            ],
        }
    ).encode()
    request = urllib.request.Request(
        GROQ_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.GROQ_TIMEOUT_SECONDS) as response:  # noqa: S310
            payload = json.load(response)
        content: str = payload["choices"][0]["message"]["content"]
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError) as error:
        raise ServiceFailed(type(error).__name__) from None
    return content


def interpret(question: str, today: date) -> dict[str, Any]:
    """The model's reading of the question: raw parameters, not yet validated."""
    if not settings.GROQ_API_KEY:
        raise NotConfigured("Questions in plain English aren't set up here: there's no Groq key.")
    try:
        reading = json.loads(_chat(_instructions(today), question))
    except ValueError:
        raise ServiceFailed("not JSON") from None
    if not isinstance(reading, dict):
        raise ServiceFailed("not an object")
    return reading


def as_query(reading: dict[str, Any]) -> dict[str, Any]:
    """The reading as explorer query parameters, for ExploreQuery to validate."""

    def listed(name: str) -> list[Any]:
        value = reading.get(name) or []
        return value if isinstance(value, list) else [value]

    query: dict[str, Any] = {
        "metric": listed("metric"),
        "by": listed("by"),
        "country": listed("country"),
        "department": listed("department"),
    }
    for name in ("currency", "as_of"):
        if reading.get(name):
            query[name] = reading[name]
    return query
