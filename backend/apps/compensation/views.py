"""An employee's salary history (design §7)."""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from apps.compensation import selectors, services
from apps.compensation.models import SalaryRecord
from apps.compensation.serializers import SalaryChangeSerializer, SalaryHistorySerializer
from apps.core import clock
from apps.core.concurrency import IF_MATCH, etag, expected_version
from apps.employees.models import Employee


def _history(employee: Employee, status: int = 200) -> Response:
    """The whole history after any change, with the employee's version for the next write."""
    rows, current = selectors.salary_history(employee, clock.today())
    body = {
        "employee_version": employee.version,
        "current_id": current.pk if current else None,
        "records": rows,
    }
    response = Response(SalaryHistorySerializer(body).data, status=status)
    response["ETag"] = etag(employee.version)
    return response


class SalaryViewSet(viewsets.ViewSet):
    @extend_schema(responses=SalaryHistorySerializer)
    def list(self, request: Request, pk: int) -> Response:
        return _history(get_object_or_404(Employee, pk=pk))

    @extend_schema(
        parameters=[IF_MATCH],
        request=SalaryChangeSerializer,
        responses={201: SalaryHistorySerializer},
    )
    def create(self, request: Request, pk: int) -> Response:
        """Record a change, back-dated or future-dated. 409 when that day already has one."""
        version = expected_version(request)
        form = SalaryChangeSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        employee = services.record_change(pk, version, **form.validated_data)
        return _history(employee, status=201)

    @extend_schema(
        parameters=[IF_MATCH], request=SalaryChangeSerializer, responses=SalaryHistorySerializer
    )
    def partial_update(self, request: Request, pk: int, sid: int) -> Response:
        """Correct a change."""
        version = expected_version(request)
        entry = get_object_or_404(
            SalaryRecord.objects.select_related("currency"), pk=sid, employee_id=pk
        )
        form = SalaryChangeSerializer(entry, data=request.data, partial=True)
        form.is_valid(raise_exception=True)
        employee = services.correct_record(pk, version, sid, form.validated_data)
        return _history(employee)

    @extend_schema(parameters=[IF_MATCH], request=None, responses=SalaryHistorySerializer)
    def destroy(self, request: Request, pk: int, sid: int) -> Response:
        """Remove a change. The starting salary can only be corrected."""
        employee = services.remove_record(pk, expected_version(request), sid)
        return _history(employee)
