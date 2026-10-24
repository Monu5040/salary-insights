"""Reading a sheet saved from Excel (design §6)."""

from datetime import date

import pytest

from domain.importing import FileError, SalaryCells, Sheet, read_sheet

HEADER = (
    "employee_code,full_name,email,country,department,job_title,"
    "hire_date,salary,currency,effective_date,reason"
)
# Written the way people type: lower case and extra spaces.
ASHA = (
    "e00007, Asha  Rao ,asha.rao@acme.example,in,Engineering,Data Analyst,"
    "2024-01-15,1800000,inr,2024-01-15,"
)


def read(*lines: str, header: str = HEADER, date_format: str = "iso", max_rows: int = 100) -> Sheet:
    content = "\n".join([header, *lines]).encode()
    return read_sheet(content, date_format=date_format, max_rows=max_rows)


def errors(*lines: str, date_format: str = "iso") -> list[tuple[int, str]]:
    return [(error.line, error.column) for error in read(*lines, date_format=date_format).errors]


def test_reads_a_clean_row_into_the_app_s_own_values() -> None:
    (row,) = read(ASHA).rows

    assert (row.line, row.employee_code, row.full_name, row.email) == (
        2,
        "E00007",
        "Asha Rao",
        "asha.rao@acme.example",
    )
    assert (row.country, row.department, row.job_title) == ("IN", "Engineering", "Data Analyst")
    assert row.hire_date == date(2024, 1, 15)
    assert row.salary == SalaryCells("1800000", "INR", date(2024, 1, 15), None)


class TestTheFile:
    def test_excel_s_byte_order_mark_is_ignored(self) -> None:
        content = ("﻿" + HEADER + "\n" + ASHA).encode()
        assert len(read_sheet(content, max_rows=10).rows) == 1

    def test_a_file_that_isnt_utf8_is_refused_with_what_to_do(self) -> None:
        content = (HEADER + "\n" + ASHA.replace("Asha", "José")).encode("cp1252")
        with pytest.raises(FileError, match="CSV UTF-8"):
            read_sheet(content, max_rows=10)

    def test_a_workbook_is_refused_with_what_to_do(self) -> None:
        with pytest.raises(FileError, match="Excel workbook"):
            read_sheet(b"PK\x03\x04rest of a zip file", max_rows=10)

    @pytest.mark.parametrize("delimiter", [";", "\t"])
    def test_semicolons_and_tabs_work_too(self, delimiter: str) -> None:
        sheet = read(ASHA.replace(",", delimiter), header=HEADER.replace(",", delimiter))
        assert sheet.rows[0].job_title == "Data Analyst"

    def test_headers_are_matched_loosely_and_unknown_columns_are_listed(self) -> None:
        header = (
            " Emp Code ,Name,E-mail,Country,Dept,Designation,DOJ,"
            "Annual Salary,Currency,Effective From,Reason,Notes"
        )
        sheet = read(ASHA + ",ignore me", header=header)

        assert sheet.rows[0].employee_code == "E00007"
        assert sheet.ignored_columns == ["Notes"]

    def test_missing_columns_stop_the_file_before_any_row(self) -> None:
        with pytest.raises(FileError, match=r"Missing columns: email, hire date\."):
            read(
                "E1,Ana",
                header="employee_code,full_name,country,department,job_title",
            )

    def test_a_salary_needs_its_currency_and_date_columns(self) -> None:
        header = "employee_code,full_name,email,country,department,job_title,hire_date,salary"
        with pytest.raises(FileError, match=r"Missing columns: currency, effective date\."):
            read("E1", header=header)

    def test_blank_rows_are_skipped_and_line_numbers_kept(self) -> None:
        sheet = read(
            "",
            ASHA,
            ",,,,",
            ASHA.replace("e00007", "E8").replace("asha.rao@acme.example", "not-an-email"),
            "",
        )

        assert [row.line for row in sheet.rows] == [3]
        assert [(error.line, error.column) for error in sheet.errors] == [(5, "email")]

    def test_too_many_rows_stop_the_file(self) -> None:
        with pytest.raises(FileError, match="3 rows; the most one file can have is 2"):
            read(ASHA, ASHA, ASHA, max_rows=2)

    @pytest.mark.parametrize("lines", [(), ("",)])
    def test_a_file_without_employees_is_refused(self, lines: tuple[str, ...]) -> None:
        with pytest.raises(FileError, match="no employees"):
            read(*lines)

    def test_quoted_cells_keep_their_commas(self) -> None:
        row = read(ASHA.replace(" Asha  Rao ", '"Rao, Asha"')).rows[0]
        assert row.full_name == "Rao, Asha"

    def test_a_cell_we_guarded_against_formulas_comes_back_as_typed(self) -> None:
        row = read(ASHA.replace("Data Analyst", "'=Lead")).rows[0]
        assert row.job_title == "=Lead"


class TestRows:
    @pytest.mark.parametrize("amount", ["$85,000", "85.000,50", "1e5", "85 000", "-5"])
    def test_formatted_numbers_are_refused_not_guessed(self, amount: str) -> None:
        assert errors(ASHA.replace("1800000", f'"{amount}"')) == [(2, "salary")]

    def test_the_same_employee_twice_flags_every_row(self) -> None:
        other = ASHA.replace("asha.rao", "someone.else")
        sheet = read(ASHA, other, ASHA.replace("e00007", "E00009"))

        assert [(error.line, error.column) for error in sheet.errors] == [
            (2, "email"),
            (2, "employee_code"),
            (3, "employee_code"),
            (4, "email"),
        ]
        assert "Also on lines 2, 3." in sheet.errors[1].message
        assert sheet.rows == []

    def test_a_bad_row_doesnt_stop_the_others(self) -> None:
        sheet = read(ASHA, ASHA.replace("e00007", "E 7").replace("asha.rao", "b"))

        assert [row.line for row in sheet.rows] == [2]
        assert [(error.line, error.column) for error in sheet.errors] == [(3, "employee_code")]

    def test_salary_cells_come_together(self) -> None:
        assert errors(ASHA.replace(",1800000,inr,", ",,inr,")) == [(2, "salary")]
        assert errors(ASHA.replace(",1800000,inr,", ",1800000,,")) == [(2, "currency")]

    def test_a_reason_must_be_one_the_app_knows(self) -> None:
        assert read(ASHA + "merit").rows[0].salary.reason == "merit"  # type: ignore[union-attr]
        assert errors(ASHA + "bonus") == [(2, "reason")]


class TestDates:
    def test_an_ambiguous_date_is_never_guessed(self) -> None:
        assert errors(ASHA.replace("2024-01-15,1800000", "03/04/2024,1800000")) == [
            (2, "hire_date")
        ]

    @pytest.mark.parametrize(
        ("date_format", "expected"), [("dmy", date(2024, 4, 3)), ("mdy", date(2024, 3, 4))]
    )
    def test_the_uploader_can_say_how_to_read_them(self, date_format: str, expected: date) -> None:
        line = ASHA.replace("2024-01-15,1800000", "03/04/2024,1800000")
        assert read(line, date_format=date_format).rows[0].hire_date == expected

    def test_iso_dates_work_whatever_the_choice(self) -> None:
        assert read(ASHA, date_format="mdy").rows[0].hire_date == date(2024, 1, 15)

    def test_a_date_that_doesnt_exist_is_an_error(self) -> None:
        line = ASHA.replace("2024-01-15,1800000", "31/02/2024,1800000")
        assert errors(line, date_format="dmy") == [(2, "hire_date")]
