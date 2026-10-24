"""The employee directory and records (design §7)."""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.concurrency import etag
from apps.core.pagination import page_of, paged_response
from apps.employees import selectors
from apps.employees.models import Employee
from apps.employees.serializers import (
    DirectoryQuery,
    EmployeePage,
    EmployeeRowSerializer,
    EmployeeSerializer,
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

    @extend_schema(responses=EmployeeSerializer)
    def retrieve(self, request: Request, pk: int) -> Response:
        return self._record(get_object_or_404(selectors.employees(), pk=pk))

    def _record(self, employee: Employee, status: int = 200) -> Response:
        """The whole record, with its version as the ETag for the next If-Match."""
        response = Response(EmployeeSerializer(employee).data, status=status)
        response["ETag"] = etag(employee.version)
        return response
