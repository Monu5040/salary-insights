"""Health probes (design §10), and the settings the SPA needs."""

from typing import Any

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import clock
from apps.core.health import database_is_reachable


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
