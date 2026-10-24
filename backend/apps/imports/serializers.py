from typing import Any

from rest_framework import serializers

DATE_FORMATS = [
    ("iso", "YYYY-MM-DD only"),
    ("dmy", "Day first, such as 31/12/2026"),
    ("mdy", "Month first, such as 12/31/2026"),
]


class UploadSerializer(serializers.Serializer[Any]):
    file = serializers.FileField(help_text="CSV, as Excel's Save As, then CSV UTF-8 writes it")
    date_format = serializers.ChoiceField(
        choices=DATE_FORMATS,
        default="iso",
        help_text="How to read dates that aren't YYYY-MM-DD; they are never guessed",
    )


class ApplySerializer(UploadSerializer):
    fingerprint = serializers.CharField(max_length=64, help_text="From the preview confirmed")


class PreviewSerializer(serializers.Serializer[Any]):
    rows = serializers.IntegerField()
    creates = serializers.IntegerField()
    changes = serializers.IntegerField()
    unchanged = serializers.IntegerField()
    error_rows = serializers.IntegerField()
    ignored_columns = serializers.ListField(child=serializers.CharField())
    new_employees = serializers.ListField(child=serializers.DictField())
    changed_employees = serializers.ListField(child=serializers.DictField())
    row_errors = serializers.ListField(child=serializers.DictField())
    fingerprint = serializers.CharField()


class AppliedSerializer(serializers.Serializer[Any]):
    creates = serializers.IntegerField()
    changes = serializers.IntegerField()
    unchanged = serializers.IntegerField()
