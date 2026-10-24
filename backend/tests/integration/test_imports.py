"""Import a sheet in two steps, and export the directory (design §6; edge cases #46 to #50,
#55, #56)."""

import csv
import io
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from pytest_django import DjangoAssertNumQueries
from pytest_django.fixtures import Settings

from apps.compensation.models import SalaryRecord
from apps.employees.models import Employee
from tests.factories import employee

pytestmark = pytest.mark.django_db

HEADER = (
    "employee_code,full_name,email,country,department,job_title,"
    "hire_date,salary,currency,effective_date,reason"
)
NEW = (
    "E00777,Asha Rao,asha.rao@acme.example,IN,Engineering,Data Analyst,"
    "2024-01-15,1800000,INR,2024-01-15,"
)


def sheet(*lines: str) -> bytes:
    return "\n".join([HEADER, *lines]).encode()


def preview(client: Client, content: bytes, **fields: Any) -> Any:
    upload = SimpleUploadedFile("employees.csv", content, content_type="text/csv")
    return client.post("/api/v1/imports/preview/", {"file": upload, **fields})


def apply(client: Client, content: bytes, fingerprint: str) -> Any:
    upload = SimpleUploadedFile("employees.csv", content, content_type="text/csv")
    return client.post("/api/v1/imports/apply/", {"file": upload, "fingerprint": fingerprint})


class TestPreview:
    def test_counts_what_would_change_and_changes_nothing(self, client: Client) -> None:
        on_file = employee(employee_code="E00001", email="kept@acme.example")
        moved = (
            f"E00001,{on_file.full_name},kept@acme.example,IN,Engineering,Staff Engineer,"
            "2024-01-15,1800000,INR,2024-01-15,"
        )

        body = preview(client, sheet(NEW, moved)).json()

        assert (body["rows"], body["creates"], body["changes"], body["unchanged"]) == (2, 1, 1, 0)
        assert body["new_employees"][0]["salary"] == "1800000 INR from 2024-01-15 (hire)"
        assert body["changed_employees"][0]["fields"] == {
            "job_title": ["Software Engineer", "Staff Engineer"]
        }
        assert Employee.objects.count() == 1

    def test_reports_every_row_error_with_its_line(self, client: Client) -> None:
        bad = (
            NEW.replace("IN,Engineering", "XX,Nowhere")
            .replace("E00777", "E00778")
            .replace("asha.rao", "b")
        )

        body = preview(client, sheet(NEW, bad)).json()

        assert [(e["line"], e["column"]) for e in body["row_errors"]] == [
            (3, "country"),
            (3, "department"),
        ]
        assert body["error_rows"] == 1

    def test_a_raise_in_the_sheet_needs_its_reason(self, client: Client) -> None:
        employee(
            employee_code="E00777",
            email="asha.rao@acme.example",
            full_name="Asha Rao",
            job_title="Data Analyst",
        )
        raised = NEW.replace(",1800000,INR,2024-01-15,", ",1926000,INR,2025-04-01,")

        body = preview(client, sheet(raised)).json()

        assert [e["column"] for e in body["row_errors"]] == ["reason"]

    def test_a_file_that_can_t_be_read_is_a_field_error(self, client: Client) -> None:
        response = preview(client, b"PK\x03\x04 a workbook")

        assert response.status_code == 400
        assert "Excel workbook" in response.json()["errors"]["file"][0]

    def test_too_big_is_refused_up_front(self, client: Client, settings: Settings) -> None:
        settings.IMPORT_MAX_MB = 0
        assert preview(client, sheet(NEW)).status_code == 400

    def test_ambiguous_dates_are_read_as_the_uploader_says(self, client: Client) -> None:
        line = NEW.replace("2024-01-15,1800000,INR,2024-01-15", "15/01/2024,1800000,INR,15/01/2024")

        assert preview(client, sheet(line)).json()["error_rows"] == 1
        assert preview(client, sheet(line), date_format="dmy").json()["creates"] == 1

    def test_plans_in_a_fixed_number_of_queries(
        self, client: Client, django_assert_num_queries: DjangoAssertNumQueries
    ) -> None:
        lines = [NEW.replace("E00777", f"E{n:05d}").replace("asha.rao", f"p{n}") for n in range(50)]
        # Countries, departments, currencies, employees on file and emails in use. Nobody is
        # on file, so there is no salary history to read.
        with django_assert_num_queries(5):
            preview(client, sheet(*lines))


class TestApply:
    def test_applies_the_previewed_plan(self, client: Client, today: date) -> None:
        content = sheet(NEW)
        fingerprint = preview(client, content).json()["fingerprint"]

        response = apply(client, content, fingerprint)

        assert response.json() == {"creates": 1, "changes": 0, "unchanged": 0}
        person = Employee.objects.get(employee_code="E00777")
        assert person.search_text == "asha rao e00777"
        assert SalaryRecord.objects.get(employee=person).amount == Decimal("1800000")

    def test_a_raise_adds_a_record_and_bumps_the_version(self, client: Client) -> None:
        person = employee(
            employee_code="E00777",
            email="asha.rao@acme.example",
            full_name="Asha Rao",
            job_title="Data Analyst",
        )
        content = sheet(NEW.replace(",1800000,INR,2024-01-15,", ",1926000,INR,2025-04-01,merit"))

        apply(client, content, preview(client, content).json()["fingerprint"])

        person.refresh_from_db()
        assert person.version == 2
        assert person.salary_records.count() == 2

    def test_importing_the_same_file_again_changes_nothing(self, client: Client) -> None:
        content = sheet(NEW)
        apply(client, content, preview(client, content).json()["fingerprint"])

        again = preview(client, content).json()

        assert (again["creates"], again["changes"], again["unchanged"]) == (0, 0, 1)

    def test_a_change_since_the_preview_is_a_409_with_a_fresh_preview(self, client: Client) -> None:
        person = employee(employee_code="E00777", email="asha.rao@acme.example")
        content = sheet(NEW)
        fingerprint = preview(client, content).json()["fingerprint"]
        person.job_title = "Changed meanwhile"
        person.version += 1
        person.save()

        response = apply(client, content, fingerprint)

        assert response.status_code == 409
        assert response.json()["preview"]["fingerprint"] != fingerprint
        person.refresh_from_db()
        assert person.full_name != "Asha Rao"

    def test_a_file_with_errors_is_never_applied_in_part(self, client: Client) -> None:
        content = sheet(NEW, NEW.replace("E00777", "E 8").replace("asha.rao", "x"))
        fingerprint = preview(client, content).json()["fingerprint"]

        response = apply(client, content, fingerprint)

        assert response.status_code == 400
        assert not Employee.objects.exists()


class TestExport:
    def test_the_directory_as_csv_that_imports_back_unchanged(
        self, client: Client, today: date
    ) -> None:
        employee(employee_code="E00001", full_name="=cmd|' /C calc'!A0", email="a@acme.example")

        response = client.get("/api/v1/exports/employees.csv")
        content = b"".join(response.streaming_content)  # type: ignore[attr-defined]

        assert response["Content-Disposition"] == 'attachment; filename="employees-2026-09-30.csv"'
        assert content.startswith("﻿".encode())  # Excel reads it as UTF-8
        _header, row = list(csv.reader(io.StringIO(content.decode().removeprefix("﻿"))))
        assert row[1].startswith("'=")  # never run as a formula
        assert (row[7], row[8], row[9]) == ("1800000.00", "INR", "2024-01-15")
        again = preview(client, content).json()
        assert (again["unchanged"], again["error_rows"]) == (1, 0)

    def test_follows_the_directory_s_filters(self, client: Client, today: date) -> None:
        employee(full_name="Ana")
        employee(full_name="Bruno")

        response = client.get("/api/v1/exports/employees.csv", {"q": "ana"})

        assert b"Ana" in b"".join(response.streaming_content)  # type: ignore[attr-defined]
