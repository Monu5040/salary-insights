"""Read settings from environment variables, failing loudly on values that don't parse."""

import os

from django.core.exceptions import ImproperlyConfigured

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def env_str(name: str, default: str | None = None) -> str:
    """The variable's value, or the default. Without a default the variable is required."""
    value = os.environ.get(name)
    if value is not None:
        return value
    if default is None:
        raise ImproperlyConfigured(f"Set the {name} environment variable.")
    return default


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    lowered = value.strip().lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    raise ImproperlyConfigured(f"{name} must be true or false, got {value!r}.")


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        raise ImproperlyConfigured(f"{name} must be a whole number, got {value!r}.") from None


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    """Comma-separated values, with blanks dropped."""
    value = os.environ.get(name)
    if value is None:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]
