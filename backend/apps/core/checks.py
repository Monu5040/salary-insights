"""Startup checks for the working assumptions (design §2 Configuration).

A bad value set through the environment stops `manage.py check`, `migrate` and the server
with a clear message, instead of surfacing later as a wrong number.
"""

from collections.abc import Sequence
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.apps import AppConfig
from django.conf import settings
from django.core.checks import CheckMessage, Error, register

POSITIVE_LIMITS = ("MIN_GROUP_SIZE", "GROQ_TIMEOUT_SECONDS", "IMPORT_MAX_MB", "IMPORT_MAX_ROWS")


@register()
def check_working_assumptions(
    app_configs: Sequence[AppConfig] | None, **kwargs: Any
) -> list[CheckMessage]:
    errors: list[CheckMessage] = []

    currency = settings.REPORTING_CURRENCY
    if not (
        len(currency) == 3 and currency.isascii() and currency.isalpha() and currency.isupper()
    ):
        errors.append(
            Error(
                f"REPORTING_CURRENCY must be an ISO-4217 code such as USD, got {currency!r}.",
                id="acme.E001",
            )
        )

    try:
        ZoneInfo(settings.ORG_TIME_ZONE)
    except (ZoneInfoNotFoundError, ValueError):
        errors.append(
            Error(
                f"ORG_TIME_ZONE must be a time zone such as Asia/Kolkata, "
                f"got {settings.ORG_TIME_ZONE!r}.",
                id="acme.E002",
            )
        )

    low, high = settings.PAY_EQUITY_BAND
    if not Decimal(0) < low < 1 < high:
        errors.append(
            Error(
                f"PAY_EQUITY_BAND must be low,high with 0 < low < 1 < high, got {low},{high}.",
                id="acme.E004",
            )
        )

    for name in POSITIVE_LIMITS:
        if getattr(settings, name) < 1:
            errors.append(Error(f"{name} must be at least 1.", id="acme.E003"))

    return errors
