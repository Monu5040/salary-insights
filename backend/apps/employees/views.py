"""The employee directory and records (design §7)."""

from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.selectors import peer_position
from apps.analytics.serializers import PeerPositionSerializer
from apps.core import clock
from apps.core.concurrency import IF_MATCH, etag, expected_version
from apps.core.pagination import page_of, paged_response
from apps.employees import selectors, services
from apps.employees.models import Employee
from apps.employees.serializers import (
    DirectoryQuery,
    EmployeePage,
    EmployeeRowSerializer,
    EmployeeSerializer,
    EmployeeWriteSerializer,
    NewEmployeeSerializer,
)
from domain.exporting import csv_lines


class EmployeeViewSet(viewsets.ViewSet):
    @extend_schema(parameters=[DirectoryQuery], responses=EmployeePage)
    def list(self, request: Request) -> Response:
        query = DirectoryQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        rows = selectors.directory(
            today=clock.today(),
            search=params["q"],
            countries=params["country"],
            departments=params["department"],
            sort=params["sort"],
        )
        count, page = page_of(rows, params["page"], params["page_size"])
        results = EmployeeRowSerializer(page, many=True).data
        return paged_response(count, params["page"], params["page_size"], results)

    @extend_schema(request=NewEmployeeSerializer, responses={201: EmployeeSerializer})
    def create(self, request: Request) -> Response:
        """Add an employee with their starting salary (409 for a code or email in use)."""
        form = NewEmployeeSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        fields = dict(form.validated_data)
        salary, currency = fields.pop("salary"), fields.pop("currency")
        employee = services.create_employee(fields, salary, currency)
        return self._record(employee.pk, status=201)

    @extend_schema(responses=EmployeeSerializer)
    def retrieve(self, request: Request, pk: int) -> Response:
        return self._record(pk)

    @extend_schema(
        parameters=[IF_MATCH], request=EmployeeWriteSerializer, responses=EmployeeSerializer
    )
    def partial_update(self, request: Request, pk: int) -> Response:
        """Change their details. The salary changes through its history."""
        version = expected_version(request)
        current = get_object_or_404(Employee, pk=pk)
        form = EmployeeWriteSerializer(current, data=request.data, partial=True)
        form.is_valid(raise_exception=True)
        services.update_employee(pk, version, form.validated_data)
        return self._record(pk)

    @extend_schema(parameters=[IF_MATCH], responses={204: None})
    def destroy(self, request: Request, pk: int) -> Response:
        services.delete_employee(pk, expected_version(request))
        return Response(status=204)

    @extend_schema(responses=PeerPositionSerializer)
    def peers(self, request: Request, pk: int) -> Response:
        """Where the employee's salary sits among people with the same job title."""
        today = clock.today()
        rows = selectors.employees(today).select_related("country__default_currency")
        position = peer_position(get_object_or_404(rows, pk=pk), today)
        if position is None:
            raise NotFound("This employee has no salary yet: their first one starts later.")
        return Response(PeerPositionSerializer(position).data)

    def _record(self, pk: int, status: int = 200) -> Response:
        """The whole record, with its version as the ETag for the next If-Match."""
        employee: Employee = get_object_or_404(selectors.employees(clock.today()), pk=pk)
        response = Response(EmployeeSerializer(employee).data, status=status)
        response["ETag"] = etag(employee.version)
        return response


class EmployeeExportView(APIView):
    """The directory as CSV, with the same filters, for Excel (design §6; edge cases #49, #50)."""

    @extend_schema(parameters=[DirectoryQuery], responses={(200, "text/csv"): OpenApiTypes.STR})
    def get(self, request: Request) -> StreamingHttpResponse:
        query = DirectoryQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        today = clock.today()
        rows = selectors.directory(
            today=today,
            search=params["q"],
            countries=params["country"],
            departments=params["department"],
            sort=params["sort"],
        )
        lines = csv_lines(selectors.EXPORT_COLUMNS, selectors.export_table(rows, today))
        response = StreamingHttpResponse(lines, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="employees-{today}.csv"'
        return response
