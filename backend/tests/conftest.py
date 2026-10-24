from datetime import date

import pytest
from hypothesis import settings

# Property-based tests must be deterministic (design §11): same examples on every run,
# no example database written to disk.
settings.register_profile("deterministic", derandomize=True, database=None, deadline=None)
settings.load_profile("deterministic")

TODAY = date(2026, 9, 30)


@pytest.fixture
def today(monkeypatch: pytest.MonkeyPatch) -> date:
    """Pins the organization's "today" (apps.core.clock) for code that asks for it."""
    monkeypatch.setattr("apps.core.clock.today", lambda: TODAY)
    return TODAY
