"""Writing CSV that Excel opens safely (design §6).

Used by the employee export.
"""

import csv
import io
from collections.abc import Iterable, Iterator
from datetime import date
from decimal import Decimal

BOM = "﻿"  # tells Excel the file is UTF-8, so non-Latin names aren't garbled
_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value: object) -> str:
    """A cell Excel won't run as a formula: text starting like one gets a leading
    apostrophe. Numbers and dates are written as they are; importing a
    guarded cell drops the apostrophe again."""
    if value is None:
        return ""
    if isinstance(value, int | Decimal | date):
        return str(value)
    text = str(value)
    return f"'{text}" if text.startswith(_FORMULA) else text


class _Line:
    """A file-like target for csv.writer that hands back each line it is given."""

    def write(self, text: str) -> str:
        return text


def csv_lines(header: Iterable[str], rows: Iterable[Iterable[object]]) -> Iterator[str]:
    """The file line by line, starting with the byte-order mark, for streaming."""
    writer = csv.writer(_Line())
    yield BOM + writer.writerow(list(header))
    for row in rows:
        yield writer.writerow([safe_cell(value) for value in row])


def csv_text(header: Iterable[str], rows: Iterable[Iterable[object]]) -> str:
    buffer = io.StringIO()
    for line in csv_lines(header, rows):
        buffer.write(line)
    return buffer.getvalue()
