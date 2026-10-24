"""The employee directory and records (design §7)."""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from apps.analytics.selectors import peer_position
from apps.analytics.serializers import PeerPositionSerializer
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
)


class EmployeeViewSet(viewsets.ViewSet):
    @extend_schema(parameters=[DirectoryQuery], responses=EmployeePage)
    def list(self, request: Request) -> Response:
        query = DirectoryQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        rows = selectors.directory(
            search=params["q"],
            countries=params["country"],
            departments=params["department"],
            sort=params["sort"],
        )
        count, page = page_of(rows, params["page"], params["page_size"])
        results = EmployeeRowSerializer(page, many=True).data
        return paged_response(count, params["page"], params["page_size"], results)

    @extend_schema(request=EmployeeWriteSerializer, responses={201: EmployeeSerializer})
    def create(self, request: Request) -> Response:
        """Add an employee with their salary (409 for a code or email in use)."""
        form = EmployeeWriteSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        employee = services.create_employee(dict(form.validated_data))
        return self._record(employee, status=201)

    @extend_schema(responses=EmployeeSerializer)
    def retrieve(self, request: Request, pk: int) -> Response:
        return self._record(get_object_or_404(selectors.employees(), pk=pk))

    @extend_schema(
        parameters=[IF_MATCH], request=EmployeeWriteSerializer, responses=EmployeeSerializer
    )
    def partial_update(self, request: Request, pk: int) -> Response:
        """Change any field, the salary included."""
        version = expected_version(request)
        current = get_object_or_404(selectors.employees(), pk=pk)
        form = EmployeeWriteSerializer(current, data=request.data, partial=True)
        form.is_valid(raise_exception=True)
        employee = services.update_employee(pk, version, form.validated_data)
        return self._record(employee)

    @extend_schema(parameters=[IF_MATCH], responses={204: None})
    def destroy(self, request: Request, pk: int) -> Response:
        services.delete_employee(pk, expected_version(request))
        return Response(status=204)

    @extend_schema(responses=PeerPositionSerializer)
    def peers(self, request: Request, pk: int) -> Response:
        """Where the employee's salary sits among people with the same job title."""
        rows = selectors.employees().select_related("country__default_currency")
        employee = get_object_or_404(rows, pk=pk)
        return Response(PeerPositionSerializer(peer_position(employee)).data)

    def _record(self, employee: Employee, status: int = 200) -> Response:
        """The whole record, with its version as the ETag for the next If-Match."""
        response = Response(EmployeeSerializer(employee).data, status=status)
        response["ETag"] = etag(employee.version)
        return response
