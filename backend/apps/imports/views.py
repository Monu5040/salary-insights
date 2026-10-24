"""Importing employees from a sheet (design §6, §7)."""

from drf_spectacular.utils import extend_schema
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.imports import services
from apps.imports.serializers import (
    AppliedSerializer,
    ApplySerializer,
    PreviewSerializer,
    UploadSerializer,
)


class PreviewView(APIView):
    parser_classes = [MultiPartParser]

    @extend_schema(request={"multipart/form-data": UploadSerializer}, responses=PreviewSerializer)
    def post(self, request: Request) -> Response:
        """What the sheet would change, with every row error. Changes nothing."""
        form = UploadSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        content = form.validated_data["file"].read()
        body = services.preview(content, form.validated_data["date_format"])
        return Response(PreviewSerializer(body).data)


class ApplyView(APIView):
    parser_classes = [MultiPartParser]

    @extend_schema(request={"multipart/form-data": ApplySerializer}, responses=AppliedSerializer)
    def post(self, request: Request) -> Response:
        """Apply the previewed sheet, whole or not at all. 409 with a fresh preview when an
        employee in it changed since."""
        form = ApplySerializer(data=request.data)
        form.is_valid(raise_exception=True)
        data = form.validated_data
        applied = services.apply(data["file"].read(), data["date_format"], data["fingerprint"])
        return Response(AppliedSerializer(applied).data)
