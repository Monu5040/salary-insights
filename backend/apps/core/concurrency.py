"""Optimistic locking over HTTP (design §7; edge case #15).

A versioned record goes out with its version as an ETag, and every write sends it back in
If-Match. The service compares it with the locked row and refuses a stale write with 412.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from apps.core.errors import PreconditionRequired

IF_MATCH = OpenApiParameter(
    "If-Match",
    OpenApiTypes.STR,
    OpenApiParameter.HEADER,
    required=True,
    description='The version you loaded, such as "3"; a newer one on the server means 412.',
)


def etag(version: int) -> str:
    return f'"{version}"'


def expected_version(request: Request) -> int:
    """The version the client last loaded, from If-Match: "3" (quotes optional)."""
    raw = request.headers.get("If-Match", "").strip()
    if not raw:
        raise PreconditionRequired(
            "Send If-Match with the version you loaded, so a newer change isn't overwritten."
        )
    tag = raw.removeprefix('"').removesuffix('"')
    if not tag.isdigit():
        raise ValidationError({"If-Match": [f'Expected a version such as "3", not {raw!r}.']})
    return int(tag)
