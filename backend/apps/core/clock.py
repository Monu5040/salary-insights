"""Today's date for business rules, where the organization is (edge case #9).

Business logic never calls date.today(): views ask this module and pass the date down, so
services and selectors take `today` as an argument and tests choose it.
"""

from datetime import date
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone


def today() -> date:
    """The current date in ORG_TIME_ZONE, not the server's."""
    return timezone.localdate(timezone=ZoneInfo(settings.ORG_TIME_ZONE))
