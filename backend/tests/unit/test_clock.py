"""Today is the organization's date, not the server's (edge case #9)."""

from datetime import UTC, date, datetime

import pytest
from pytest_django.fixtures import Settings

from apps.core import clock

# 20:00 in London is already the next morning in India.
LATE_EVENING_UTC = datetime(2026, 9, 30, 20, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("zone", "expected"),
    [("UTC", date(2026, 9, 30)), ("Asia/Kolkata", date(2026, 10, 1))],
)
def test_today_follows_the_organizations_time_zone(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, zone: str, expected: date
) -> None:
    settings.ORG_TIME_ZONE = zone
    monkeypatch.setattr("django.utils.timezone.now", lambda: LATE_EVENING_UTC)

    assert clock.today() == expected
