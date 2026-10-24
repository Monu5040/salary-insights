import re
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.utils.cache import patch_cache_control

HEADER = "X-Request-ID"
_VALID = re.compile(r"[A-Za-z0-9._-]{8,64}")


class RequestIdMiddleware:
    """Give every request an id: the platform's when it sends a sane one, else a new one.

    The id goes back in the response and in error bodies, so a report like "my save failed"
    can be traced through the logs.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        incoming = request.headers.get(HEADER, "")
        request_id = incoming if _VALID.fullmatch(incoming) else uuid.uuid4().hex
        request.request_id = request_id  # type: ignore[attr-defined]
        response = self.get_response(request)
        response[HEADER] = request_id
        return response


class PrivateApiCacheMiddleware:
    """API responses carry pay data: a browser may keep them, a shared cache never (#27)."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        if request.path.startswith("/api/") and not response.has_header("Cache-Control"):
            patch_cache_control(response, private=True, no_cache=True)
        return response
