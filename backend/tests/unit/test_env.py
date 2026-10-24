from decimal import Decimal

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.env import env_bool, env_decimal_pair, env_int, env_list, env_str

VAR = "ACME_TEST_SETTING"


def test_env_str_prefers_the_variable_over_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(VAR, "from-env")
    assert env_str(VAR, "default") == "from-env"


def test_env_str_falls_back_to_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(VAR, raising=False)
    assert env_str(VAR, "default") == "default"


def test_env_str_without_a_default_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(VAR, raising=False)
    with pytest.raises(ImproperlyConfigured, match=VAR):
        env_str(VAR)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("true", True), ("1", True), ("Yes", True), (" on ", True), ("false", False), ("0", False)],
)
def test_env_bool_accepts_common_spellings(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: bool
) -> None:
    monkeypatch.setenv(VAR, raw)
    assert env_bool(VAR, default=not expected) is expected


def test_env_bool_rejects_anything_else(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(VAR, "maybe")
    with pytest.raises(ImproperlyConfigured, match="true or false"):
        env_bool(VAR, default=False)


def test_env_int_rejects_words(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(VAR, "ten")
    with pytest.raises(ImproperlyConfigured, match="whole number"):
        env_int(VAR, default=10)


def test_env_list_splits_on_commas_and_drops_blanks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(VAR, "a.example.com, b.example.com,,")
    assert env_list(VAR) == ["a.example.com", "b.example.com"]


def test_env_decimal_pair_reads_low_and_high(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(VAR, "0.75, 1.25")
    assert env_decimal_pair(VAR, "0.80,1.20") == (Decimal("0.75"), Decimal("1.25"))


@pytest.mark.parametrize("raw", ["0.8", "low,high", "1,2,3"])
def test_env_decimal_pair_rejects_anything_but_two_numbers(
    monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    monkeypatch.setenv(VAR, raw)
    with pytest.raises(ImproperlyConfigured, match="two numbers"):
        env_decimal_pair(VAR, "0.80,1.20")
