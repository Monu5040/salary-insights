"""Health probes (design §10), and the settings the SPA needs."""

from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseNotFound, JsonResponse
from django.utils.cache import patch_cache_control
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_safe
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import clock
from apps.core.health import database_is_reachable


@require_safe
def spa(request: HttpRequest) -> HttpResponse:
    """The React app's page, for every address the app handles (design §2). Served by Django
    so it carries the security headers, and revalidated on every load, so a deploy is picked
    up at once; its scripts and styles are hashed static files, cached for good."""
    try:
        page = (settings.SPA_DIR / "index.html").read_bytes()
    except FileNotFoundError:
        return HttpResponseNotFound(
            "The app isn't built. Run `npm run build` in frontend/, or use `make dev`.",
            content_type="text/plain",
        )
    response = HttpResponse(page, content_type="text/html; charset=utf-8")
    patch_cache_control(response, no_cache=True)
    return response


@never_cache
@require_GET
def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness: the process answers. It never touches the database, so a database
    blip doesn't make the platform restart the app."""
    return JsonResponse({"status": "ok"})


@never_cache
@require_GET
def readyz(request: HttpRequest) -> JsonResponse:
    """Readiness: take traffic only while the database answers."""
    if database_is_reachable():
        return JsonResponse({"status": "ok"})
    return JsonResponse({"status": "unavailable"}, status=503)


class ConfigSerializer(serializers.Serializer[Any]):
    reporting_currency = serializers.CharField()
    today = serializers.DateField(help_text="Today in the organization's time zone")


class ConfigView(APIView):
    """Working assumptions the screens follow (design §2), and the organization's today, so
    default dates don't depend on the browser's time zone."""

    @extend_schema(responses=ConfigSerializer)
    def get(self, request: Request) -> Response:
        config = {
            "reporting_currency": settings.REPORTING_CURRENCY,
            "today": clock.today(),
        }
        return Response(ConfigSerializer(config).data)
