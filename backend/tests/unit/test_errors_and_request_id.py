"""problem+json errors and request ids (design §7, §9)."""

import json

import pytest
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory
from rest_framework.exceptions import NotFound, Throttled, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from apps.core.concurrency import expected_version
from apps.core.errors import PROBLEM_JSON, Conflict, PreconditionFailed, PreconditionRequired
from apps.core.middleware import RequestIdMiddleware


class Raises(APIView):
    """A view that raises the error under test, so DRF renders it as it would in production."""

    authentication_classes: list[type] = []
    permission_classes: list[type] = []
    error: Exception = RuntimeError()

    def get(self, request: Request) -> Response:
        raise self.error


def call(error: Exception) -> Response:
    request = APIRequestFactory().get("/")
    request.request_id = "req-12345678"  # type: ignore[attr-defined]
    response: Response = Raises.as_view(error=error)(request)
    response.render()
    return response


def test_errors_are_problem_json_with_the_request_id() -> None:
    response = call(NotFound())

    assert response["Content-Type"] == PROBLEM_JSON
    assert json.loads(response.content) == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "Not found.",
        "request_id": "req-12345678",
    }


def test_validation_errors_list_each_field() -> None:
    response = call(ValidationError({"email": ["This field is required."]}))

    assert response.status_code == 400
    assert json.loads(response.content)["errors"] == {"email": ["This field is required."]}


def test_a_rule_about_the_whole_request_is_the_detail() -> None:
    body = json.loads(call(ValidationError("The starting salary can't be removed.")).content)
    assert (body["status"], body["detail"]) == (400, "The starting salary can't be removed.")
    assert "errors" not in body


def test_retry_after_is_kept() -> None:
    assert call(Throttled(wait=60))["Retry-After"] == "60"


def test_a_conflict_names_the_field_and_the_record_it_clashes_with() -> None:
    error = Conflict("Taken.", errors={"email": ["Taken."]}, existing_id=7)

    body = json.loads(call(error).content)

    assert (body["status"], body["errors"], body["existing_id"]) == (409, {"email": ["Taken."]}, 7)


def test_a_stale_write_says_which_version_the_server_has() -> None:
    body = json.loads(call(PreconditionFailed("Reload.", current_version=4)).content)
    assert (body["status"], body["detail"], body["current_version"]) == (412, "Reload.", 4)


def test_unexpected_errors_are_left_to_django() -> None:
    with pytest.raises(RuntimeError):
        call(RuntimeError("boom"))


def respond(request: HttpRequest) -> HttpResponse:
    return HttpResponse("ok")


def test_every_response_carries_a_new_request_id() -> None:
    response = RequestIdMiddleware(respond)(RequestFactory().get("/"))
    assert len(response["X-Request-ID"]) == 32


def test_a_sane_platform_request_id_is_kept() -> None:
    request = RequestFactory().get("/", HTTP_X_REQUEST_ID="edge-7f3a9c21")
    assert RequestIdMiddleware(respond)(request)["X-Request-ID"] == "edge-7f3a9c21"


@pytest.mark.parametrize("incoming", ["short", "has spaces in it", "x" * 65, "<script>"])
def test_a_suspicious_request_id_is_replaced(incoming: str) -> None:
    request = RequestFactory().get("/", HTTP_X_REQUEST_ID=incoming)
    assert RequestIdMiddleware(respond)(request)["X-Request-ID"] != incoming


def if_match(value: str | None) -> Request:
    headers = {} if value is None else {"If-Match": value}
    return Request(APIRequestFactory().patch("/", headers=headers))


@pytest.mark.parametrize("value", ['"3"', "3", ' "3" '])
def test_if_match_carries_the_version_the_client_loaded(value: str) -> None:
    assert expected_version(if_match(value)) == 3


def test_a_write_without_if_match_is_refused_with_428() -> None:
    with pytest.raises(PreconditionRequired):
        expected_version(if_match(None))


@pytest.mark.parametrize("value", ['W/"3"', "three", '"-1"', "*"])
def test_an_if_match_that_isnt_a_version_is_a_400(value: str) -> None:
    with pytest.raises(ValidationError):
        expected_version(if_match(value))
