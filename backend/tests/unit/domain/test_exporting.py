"""Writing CSV that Excel opens safely (edge cases #49, #50)."""

from datetime import date
from decimal import Decimal

import pytest

from domain.exporting import BOM, csv_text, safe_cell
from domain.importing import read_sheet


@pytest.mark.parametrize(
    ("value", "written"),
    [
        ('=HYPERLINK("http://evil")', '\'=HYPERLINK("http://evil")'),
        ("+1 555 0100", "'+1 555 0100"),
        ("-negative", "'-negative"),
        ("@SUM(A1)", "'@SUM(A1)"),
        ("José Núñez", "José Núñez"),
        (Decimal("1926000.00"), "1926000.00"),
        (date(2024, 1, 15), "2024-01-15"),
        (None, ""),
    ],
)
def test_text_that_looks_like_a_formula_is_guarded(value: object, written: str) -> None:
    assert safe_cell(value) == written


def test_the_file_starts_with_the_byte_order_mark_and_quotes_what_it_must() -> None:
    text = csv_text(["name", "salary"], [["Rao, Asha", Decimal("1800000.00")], ["山田 太郎", 5]])

    assert text.startswith(BOM + "name,salary\r\n")
    assert text.splitlines()[1:] == ['"Rao, Asha",1800000.00', "山田 太郎,5"]


def test_an_exported_cell_imports_back_as_it_was() -> None:
    header = [
        "employee_code",
        "full_name",
        "email",
        "country",
        "department",
        "level",
        "job_title",
        "employment_type",
        "hire_date",
    ]
    row = [
        "E1",
        "Ana",
        "ana@acme.example",
        "IN",
        "Engineering",
        "L3",
        "=Lead",
        "full_time",
        "2024-01-15",
    ]

    (back,) = read_sheet(csv_text(header, [row]).encode(), max_rows=10).rows

    assert back.job_title == "=Lead"
