"""API errors as RFC 9457 problem+json, with field errors and the request id (design §7)."""

from http import HTTPStatus
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import defaults
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

PROBLEM_JSON = "application/problem+json"


class ApiProblem(APIException):
    """An API error whose body says more than `detail`, such as field errors, the record
    it clashes with, or the version the server has. The extra fields join the problem body."""

    def __init__(self, detail: str, **extra: Any) -> None:
        super().__init__(detail)
        self.extra = extra


class Conflict(ApiProblem):
    """409: the request clashes with another record, such as a duplicate email (#10, #16)."""

    status_code = 409
    default_code = "conflict"


class PreconditionFailed(ApiProblem):
    """412: the record changed since the client loaded it (If-Match; edge case #15)."""

    status_code = 412
    default_code = "stale_version"


class Unprocessable(ApiProblem):
    """422: a valid request the data can't answer, such as an unknown currency (#4)."""

    status_code = 422
    default_code = "unprocessable"


class PreconditionRequired(ApiProblem):
    """428: a write to a versioned record came without If-Match."""

    status_code = 428
    default_code = "if_match_required"


def problem_body(
    status: int, detail: str, *, errors: Any = None, request_id: str = "", **extra: Any
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": HTTPStatus(status).phrase,
        "status": status,
        "detail": detail,
    }
    if errors:
        body["errors"] = errors
    body.update(extra)
    if request_id:
        body["request_id"] = request_id
    return body


def problem(
    status: int, detail: str, *, errors: Any = None, request_id: str = "", **extra: Any
) -> Response:
    body = problem_body(status, detail, errors=errors, request_id=request_id, **extra)
    return Response(body, status=status, content_type=PROBLEM_JSON)


def page_not_found(request: HttpRequest, exception: Exception) -> HttpResponse:
    """Django's 404 (handler404), for an address no view matches: problem+json under /api/
    (edge case #32), Django's own page elsewhere."""
    if not request.path.startswith("/api/"):
        return defaults.page_not_found(request, exception)
    return _django_problem(request, 404, "There is nothing at this address.")


def server_error(request: HttpRequest) -> HttpResponse:
    """Django's 500 (handler500), for an error no view handled: problem+json under /api/ with
    the request id to quote (edge case #32), and never the error itself, which may hold data."""
    if not request.path.startswith("/api/"):
        return defaults.server_error(request)
    return _django_problem(request, 500, "Something went wrong on our side.")


def _django_problem(request: HttpRequest, status: int, detail: str) -> JsonResponse:
    """A problem for errors Django answers itself, outside DRF's views."""
    body = problem_body(status, detail, request_id=getattr(request, "request_id", ""))
    return JsonResponse(body, status=status, content_type=PROBLEM_JSON)


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    response = drf_exception_handler(exc, context)
    if response is None:
        return None  # not an API error: Django's own 500 handling applies
    request_id = getattr(context.get("request"), "request_id", "")
    if isinstance(exc, ValidationError) and isinstance(response.data, dict):
        result = problem(
            response.status_code,
            "Some fields need attention.",
            errors=response.data,
            request_id=request_id,
        )
    elif isinstance(exc, ValidationError):
        # A rule about the request as a whole, such as "the starting salary can't be removed".
        detail = " ".join(str(message) for message in response.data)
        result = problem(response.status_code, detail, request_id=request_id)
    else:
        data = response.data
        detail = data.get("detail", "") if isinstance(data, dict) else str(data)
        extra = exc.extra if isinstance(exc, ApiProblem) else {}
        result = problem(response.status_code, str(detail), request_id=request_id, **extra)
    for header in ("WWW-Authenticate", "Retry-After"):
        if header in response:
            result[header] = response[header]
    return result
