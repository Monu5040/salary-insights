"""Page numbers with a total (D8; edge case #18)."""

from typing import Any

from django.db.models import Model, QuerySet
from rest_framework import serializers
from rest_framework.response import Response

from apps.core.query import StrictQuery

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 200


class PageQuery(StrictQuery):
    """`page` and `page_size`. A size above the cap is capped, not refused."""

    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, default=DEFAULT_PAGE_SIZE)

    def validate_page_size(self, value: int) -> int:
        return min(value, MAX_PAGE_SIZE)


def page_of[ModelT: Model](
    queryset: QuerySet[ModelT], page: int, page_size: int
) -> tuple[int, list[ModelT]]:
    """The total and one page of rows: two queries. A page past the end is empty, with the
    true total, where DRF's paginator would answer 404."""
    count = queryset.count()
    start = (page - 1) * page_size
    return count, list(queryset[start : start + page_size]) if start < count else []


def page_of_list[T](rows: list[T], page: int, page_size: int) -> tuple[int, list[T]]:
    """The same, for rows already in memory."""
    start = (page - 1) * page_size
    return len(rows), rows[start : start + page_size]


def paged_response(count: int, page: int, page_size: int, results: Any) -> Response:
    return Response({"count": count, "page": page, "page_size": page_size, "results": results})
