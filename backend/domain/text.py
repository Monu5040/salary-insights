"""Text rules for names, codes and search (design §3 search_text; edge cases #10, #11)."""

import re
import unicodedata


def fold(text: str) -> str:
    """Lower-case, strip accents and collapse spaces: "José  Núñez" becomes "jose nunez".

    The same function folds stored names and typed queries, so "jose" finds "José".
    """
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(stripped.casefold().split())


def clean_name(text: str) -> str:
    """A person's name as stored: NFC-normalized, runs of spaces collapsed (edge case #11).

    NFC makes "é" typed as one character or as "e" plus an accent the same stored text.
    """
    return " ".join(unicodedata.normalize("NFC", text).split())


class InvalidCode(ValueError):
    """An employee code with characters a business key shouldn't have."""


_CODE = re.compile(r"[A-Z0-9][A-Z0-9._-]{0,31}")


def employee_code(raw: str) -> str:
    """An employee code as stored: trimmed and upper-case, so "e00042 " and "E00042" are
    the same employee (edge case #10). Letters, digits, ".", "_" and "-" only."""
    code = raw.strip().upper()
    if not _CODE.fullmatch(code):
        raise InvalidCode(
            "Use up to 32 letters, digits, '.', '_' or '-', starting with a letter or digit."
        )
    return code
