from typing import Any

from rest_framework import serializers


class StrictQuery(serializers.Serializer[Any]):
    """A query string whose parameters are all listed: anything else is a 400 naming it,
    where DRF would silently ignore it (edge case #21)."""

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(self.initial_data) - set(self.fields))
        if unknown:
            allowed = ", ".join(self.fields)
            raise serializers.ValidationError(
                {name: [f"Unknown parameter. Use {allowed}."] for name in unknown}
            )
        return attrs
