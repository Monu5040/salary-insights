"""Reading an employee sheet saved from Excel as CSV (design §6).

Pure Python: bytes in, rows and errors out. Everything that needs the database (unknown
countries, emails already in use, salaries already on file) is checked by the caller.
"""

import csv
import io
import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from domain.text import InvalidCode, clean_name, employee_code

BOM = "﻿"
DATE_FORMATS = ("iso", "dmy", "mdy")


Fail = Callable[[str, str], None]  # records an error on a column of the row being read


class FileError(ValueError):
    """A problem with the file as a whole: nothing in it is imported."""


# Each column and the headers that mean it, compared without case, spaces or punctuation.
COLUMNS: dict[str, tuple[str, ...]] = {
    "employee_code": ("employee code", "emp code", "code", "employee id", "emp id", "employee no"),
    "full_name": ("full name", "name", "employee name"),
    "email": ("email", "work email", "email address", "e mail"),
    "country": ("country", "country code"),
    "department": ("department", "dept"),
    "job_title": ("job title", "title", "role", "position", "designation"),
    "hire_date": ("hire date", "start date", "joining date", "date of joining", "doj"),
    "salary": ("salary", "annual salary", "base salary", "amount"),
    "currency": ("currency", "salary currency"),
    "effective_date": ("effective date", "salary date", "effective from"),
    "reason": ("reason", "change reason"),
}
REQUIRED = (
    "employee_code",
    "full_name",
    "email",
    "country",
    "department",
    "job_title",
    "hire_date",
)
SALARY = ("salary", "currency", "effective_date")
REASONS = ("hire", "merit", "promotion", "market", "transfer", "correction")

_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_PARTS_DATE = re.compile(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})")
_PLAIN_NUMBER = re.compile(r"\d+(\.\d+)?")
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def _words(text: str) -> str:
    """ "Emp_Code " and "EMP-CODE" both read as "emp code"."""
    return " ".join(re.sub(r"[^0-9a-z]+", " ", text.casefold()).split())


_HEADERS = {
    _words(alias): column for column, aliases in COLUMNS.items() for alias in (column, *aliases)
}


@dataclass(frozen=True)
class SalaryCells:
    amount: str  # checked against the currency's decimals and ceiling by the caller
    currency: str
    effective_date: date
    reason: str | None  # None: a hire for a new employee, otherwise required


@dataclass(frozen=True)
class Row:
    line: int  # in the file, counting the header as line 1
    employee_code: str
    full_name: str
    email: str
    country: str
    department: str
    job_title: str
    hire_date: date
    salary: SalaryCells | None


@dataclass(frozen=True)
class RowError:
    line: int
    column: str
    message: str


@dataclass(frozen=True)
class Sheet:
    rows: list[Row]
    errors: list[RowError]
    ignored_columns: list[str]


def read_sheet(content: bytes, *, date_format: str = "iso", max_rows: int) -> Sheet:
    """Every row of the file, checked, or a FileError when the file itself can't be used."""
    text = _decode(content)
    lines = text.splitlines()
    if not lines or not lines[0].strip():
        raise FileError("The file is empty: it needs a header row and at least one employee.")
    delimiter = _delimiter(lines[0])
    table = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    header, *body = table
    columns, ignored = _columns(header)
    numbered = [
        (index + 2, cells) for index, cells in enumerate(body) if any(c.strip() for c in cells)
    ]
    if len(numbered) > max_rows:
        raise FileError(
            f"The file has {len(numbered):,} rows; the most one file can have is {max_rows:,}."
        )
    if not numbered:
        raise FileError("The file has a header but no employees.")

    rows: list[Row] = []
    errors: list[RowError] = []
    for line, cells in numbered:
        values = {column: _cell(cells, index) for column, index in columns.items()}
        row, row_errors = _read_row(line, values, date_format)
        errors += row_errors
        if row is not None:
            rows.append(row)
    errors += _duplicates(rows)
    flagged = {error.line for error in errors}
    return Sheet(
        [row for row in rows if row.line not in flagged], sorted(errors, key=_order), ignored
    )


def _order(error: RowError) -> tuple[int, str]:
    return error.line, error.column


def _decode(content: bytes) -> str:
    """UTF-8, with or without the byte-order mark Excel writes."""
    if content.startswith(b"PK\x03\x04"):
        raise FileError("That's an Excel workbook. In Excel choose Save As, then CSV UTF-8.")
    try:
        return content.decode("utf-8").removeprefix(BOM)
    except UnicodeDecodeError:
        raise FileError(
            "The file isn't UTF-8 text, so names could come out garbled. "
            "In Excel choose Save As, then CSV UTF-8."
        ) from None


def _delimiter(header: str) -> str:
    """Comma, semicolon (European Excel) or tab: whichever splits the header."""
    counts = {delimiter: header.count(delimiter) for delimiter in (",", ";", "\t")}
    best = max(counts, key=lambda delimiter: counts[delimiter])
    if counts[best] == 0:
        raise FileError("The header has one column: separate columns with commas or semicolons.")
    return best


def _columns(header: list[str]) -> tuple[dict[str, int], list[str]]:
    """Which column is which, by header text, without case, spaces or punctuation."""
    columns: dict[str, int] = {}
    ignored: list[str] = []
    for index, title in enumerate(header):
        column = _HEADERS.get(_words(title))
        if column is None or column in columns:
            if title.strip():
                ignored.append(title.strip())
            continue
        columns[column] = index
    missing = [column for column in REQUIRED if column not in columns]
    if any(column in columns for column in SALARY):
        missing += [column for column in SALARY if column not in columns]
    if missing:
        names = ", ".join(column.replace("_", " ") for column in missing)
        raise FileError(f"Missing columns: {names}.")
    return columns, ignored


def _cell(cells: list[str], index: int) -> str:
    value = cells[index].strip() if index < len(cells) else ""
    # A cell we exported as text, guarded against spreadsheet formulas, comes back as typed.
    if value[:1] == "'" and value[1:2] in ("=", "+", "-", "@"):
        return value[1:]
    return value


def _read_row(
    line: int, values: dict[str, str], date_format: str
) -> tuple[Row | None, list[RowError]]:
    errors: list[RowError] = []

    def fail(column: str, message: str) -> None:
        errors.append(RowError(line, column, message))

    def text(column: str, longest: int) -> str:
        value = values.get(column, "")
        if not value:
            fail(column, "Required.")
        elif len(value) > longest:
            fail(column, f"At most {longest} characters.")
        return value

    code = ""
    try:
        code = employee_code(values.get("employee_code", ""))
    except InvalidCode as error:
        fail("employee_code", str(error))
    name = clean_name(text("full_name", 200))
    email = text("email", 254)
    if email and not _EMAIL.fullmatch(email):
        fail("email", "Not an email address.")
    country = text("country", 2).upper()
    department = " ".join(text("department", 100).split())
    job_title = text("job_title", 120)

    hire_date = _date(values.get("hire_date", ""), date_format, "hire_date", fail)
    salary = _salary(values, date_format, fail)

    if errors or hire_date is None:
        return None, errors
    row = Row(line, code, name, email, country, department, job_title, hire_date, salary)
    return row, errors


def _date(raw: str, date_format: str, column: str, fail: Fail) -> date | None:
    """ISO dates always; 03/04/2026 only when the uploader said how to read it."""
    if not raw:
        fail(column, "Required.")
        return None
    try:
        if _ISO_DATE.fullmatch(raw):
            return date.fromisoformat(raw)
        parts = _PARTS_DATE.fullmatch(raw)
        if parts is None or date_format == "iso":
            fail(
                column,
                "Write the date as YYYY-MM-DD, or choose the file's date format when uploading.",
            )
            return None
        first, second, year = (int(part) for part in parts.groups())
        day, month = (first, second) if date_format == "dmy" else (second, first)
        return date(year, month, day)
    except ValueError:
        fail(column, f"{raw} isn't a real date.")
        return None


def _salary(values: dict[str, str], date_format: str, fail: Fail) -> SalaryCells | None:
    """All of salary, currency and effective date, or none of them."""
    if not any(values.get(column) for column in SALARY):
        return None
    amount = values.get("salary", "")
    if not amount:
        fail("salary", "Required with a currency and effective date.")
    elif not _PLAIN_NUMBER.fullmatch(amount):
        fail("salary", "Write a plain number such as 85000.50: no currency signs or separators.")
    currency = values.get("currency", "").upper()
    if not re.fullmatch(r"[A-Z]{3}", currency):
        fail("currency", "Write a three-letter currency code, such as INR.")
    effective = _date(values.get("effective_date", ""), date_format, "effective_date", fail)
    reason = values.get("reason", "").casefold() or None
    if reason is not None and reason not in REASONS:
        fail("reason", f"Write one of: {', '.join(REASONS)}.")
    if effective is None:
        return None
    return SalaryCells(amount, currency, effective, reason)


def _code_of(row: Row) -> str:
    return row.employee_code


def _email_of(row: Row) -> str:
    return row.email.casefold()  # emails are unique in any case


def _duplicates(rows: list[Row]) -> list[RowError]:
    """Every row of an employee code or email that appears more than once."""
    errors: list[RowError] = []
    keys: list[tuple[str, Callable[[Row], str]]] = [
        ("employee_code", _code_of),
        ("email", _email_of),
    ]
    for column, key in keys:
        lines: dict[str, list[int]] = defaultdict(list)
        for row in rows:
            lines[key(row)].append(row.line)
        for value_lines in lines.values():
            if len(value_lines) > 1:
                where = ", ".join(map(str, value_lines))
                errors += [
                    RowError(line, column, f"Also on lines {where}.") for line in value_lines
                ]
    return errors
