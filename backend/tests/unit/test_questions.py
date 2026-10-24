"""The Groq client behind questions in plain English (design §4), with no network."""

import io
import json
import urllib.error
from typing import Any

import pytest
from pytest_django.fixtures import Settings

from apps.analytics import questions


class FakeResponse(io.BytesIO):
    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def test_asks_for_json_with_the_key_and_reads_the_reply(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.GROQ_API_KEY = "test-key"
    seen: dict[str, Any] = {}

    def urlopen(request: Any, timeout: int) -> FakeResponse:
        seen["auth"] = request.get_header("Authorization")
        seen["body"] = json.loads(request.data)
        reply = {"choices": [{"message": {"content": '{"metric": ["median"]}'}}]}
        return FakeResponse(json.dumps(reply).encode())

    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    assert questions._chat("system", "question") == '{"metric": ["median"]}'
    assert seen["auth"] == "Bearer test-key"
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert seen["body"]["temperature"] == 0


@pytest.mark.parametrize(
    "failure",
    [urllib.error.URLError("down"), TimeoutError()],
)
def test_a_service_that_doesn_t_answer_is_a_failure_not_a_crash(
    monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    def urlopen(request: Any, timeout: int) -> FakeResponse:
        raise failure

    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    with pytest.raises(questions.ServiceFailed):
        questions._chat("system", "question")


def test_a_reply_without_a_message_is_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda request, timeout: FakeResponse(b'{"choices": []}')
    )
    with pytest.raises(questions.ServiceFailed):
        questions._chat("system", "question")


def test_a_reading_becomes_explorer_parameters() -> None:
    reading = {"metric": "median", "by": None, "country": ["IN"], "currency": "EUR", "as_of": None}

    assert questions.as_query(reading) == {
        "metric": ["median"],
        "by": [],
        "country": ["IN"],
        "department": [],
        "currency": "EUR",
    }
