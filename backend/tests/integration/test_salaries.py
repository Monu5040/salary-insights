"""An employee's salary history (design §6, §7; edge cases #15, #41 to #45)."""

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.test import Client
from pytest_django import DjangoAssertNumQueries

from apps.compensation.models import SalaryRecord
from apps.employees.models import Employee
from tests.factories import employee, record

pytestmark = pytest.mark.django_db


def url(person: Employee, sid: int | None = None) -> str:
    base = f"/api/v1/employees/{person.pk}/salaries/"
    return base if sid is None else f"{base}{sid}/"


def change(**overrides: Any) -> dict[str, Any]:
    body = {
        "effective_date": "2025-04-01",
        "amount": "1926000",
        "currency": "INR",
        "reason": "merit",
        "note": "",
    }
    return body | overrides


def send(client: Client, method: str, path: str, body: Any, version: int) -> Any:
    call = getattr(client, method)
    return call(path, body, content_type="application/json", headers={"If-Match": f'"{version}"'})


class TestHistory:
    def test_newest_first_with_the_raise_and_the_one_in_force(
        self, client: Client, today: date
    ) -> None:
        person = employee()
        raised = record(
            person, effective_date=date(2025, 4, 1), amount=Decimal("1926000"), reason="merit"
        )
        record(person, effective_date=date(2027, 4, 1), amount=Decimal("2000000"), reason="merit")

        body = client.get(url(person)).json()

        rows = [(r["effective_date"], r["raise_percent"], r["scheduled"]) for r in body["records"]]
        assert rows == [
            ("2027-04-01", "3.84", True),
            ("2025-04-01", "7.00", False),
            ("2024-01-15", None, False),
        ]
        assert (body["current_id"], body["employee_version"]) == (raised.pk, 1)

    def test_a_currency_change_is_not_a_raise(self, client: Client, today: date) -> None:
        person = employee()
        record(
            person,
            effective_date=date(2025, 7, 1),
            amount=Decimal("30000"),
            currency_id="USD",
            reason="transfer",
        )

        (latest, _) = client.get(url(person)).json()["records"]

        assert (latest["raise_percent"], latest["currency_change"]) == (None, True)

    def test_reads_in_a_fixed_number_of_queries(
        self, client: Client, today: date, django_assert_num_queries: DjangoAssertNumQueries
    ) -> None:
        person = employee()
        for year in (2025, 2026):
            record(
                person,
                effective_date=date(year, 4, 1),
                amount=Decimal(2_000_000 + year),
                reason="merit",
            )
        with django_assert_num_queries(2):  # the employee, then the records
            client.get(url(person))


class TestRecordChange:
    def test_a_back_dated_change_takes_its_place(self, client: Client, today: date) -> None:
        person = employee()
        record(person, effective_date=date(2026, 4, 1), amount=Decimal("2100000"), reason="merit")

        response = send(client, "post", url(person), change(), version=1)

        assert response.status_code == 201
        records = response.json()["records"]
        assert [r["effective_date"] for r in records] == ["2026-04-01", "2025-04-01", "2024-01-15"]
        assert records[0]["raise_percent"] == "9.03"  # now against the back-dated change
        assert response.json()["employee_version"] == 2

    def test_a_future_change_is_scheduled_and_today_s_salary_stays(
        self, client: Client, today: date
    ) -> None:
        person = employee()

        send(client, "post", url(person), change(effective_date="2027-01-01"), version=1)

        assert client.get(f"/api/v1/employees/{person.pk}/").json()["salary"] == "1800000.00"

    def test_shows_in_the_directory_once_in_force(self, client: Client, today: date) -> None:
        person = employee()

        send(client, "post", url(person), change(effective_date="2026-09-30"), version=1)

        (row,) = client.get("/api/v1/employees/").json()["results"]
        assert row["salary"] == "1926000.00"

    def test_not_before_the_hire_date(self, client: Client) -> None:
        person = employee()

        response = send(client, "post", url(person), change(effective_date="2024-01-14"), version=1)

        assert response.status_code == 400
        assert "on or after the hire date" in response.json()["errors"]["effective_date"][0]

    def test_a_second_change_on_one_day_points_at_the_first(self, client: Client) -> None:
        person = employee()
        first = send(client, "post", url(person), change(), version=1).json()["records"][0]

        response = send(client, "post", url(person), change(amount="1"), version=2)

        assert response.status_code == 409
        assert response.json()["existing_id"] == first["id"]

    def test_only_the_starting_salary_is_a_hire(self, client: Client) -> None:
        person = employee()
        assert send(client, "post", url(person), change(reason="hire"), 1).status_code == 400

    def test_the_amount_must_fit_its_currency(self, client: Client) -> None:
        person = employee()

        response = send(client, "post", url(person), change(amount="5.5", currency="JPY"), 1)

        assert "at most 0 decimal places" in response.json()["errors"]["amount"][0]

    def test_a_stale_version_is_refused(self, client: Client) -> None:
        person = employee()
        send(client, "post", url(person), change(), version=1)

        assert (
            send(client, "post", url(person), change(effective_date="2026-01-01"), 1).status_code
            == 412
        )
        assert SalaryRecord.objects.filter(employee=person).count() == 2


class TestCorrectAndRemove:
    def test_a_correction_fixes_the_amount(self, client: Client) -> None:
        person = employee()
        entry = record(
            person, effective_date=date(2025, 4, 1), amount=Decimal("1926000"), reason="merit"
        )

        response = send(client, "patch", url(person, entry.pk), {"amount": "1930000"}, 1)

        assert response.status_code == 200
        entry.refresh_from_db()
        assert entry.amount == Decimal("1930000")

    def test_a_new_currency_is_checked_against_the_amount_on_record(self, client: Client) -> None:
        person = employee()
        entry = record(
            person, effective_date=date(2025, 4, 1), amount=Decimal("1926000.50"), reason="merit"
        )

        response = send(client, "patch", url(person, entry.pk), {"currency": "JPY"}, 1)

        assert response.status_code == 400

    def test_correcting_nothing_keeps_the_version(self, client: Client) -> None:
        person = employee()
        entry = record(
            person, effective_date=date(2025, 4, 1), amount=Decimal("1926000"), reason="merit"
        )

        response = send(client, "patch", url(person, entry.pk), {"amount": "1926000"}, 1)

        assert response.json()["employee_version"] == 1

    def test_the_starting_salary_stays_a_hire_on_the_hire_date(self, client: Client) -> None:
        person = employee()
        hire = person.salary_records.get()

        moved = send(client, "patch", url(person, hire.pk), {"effective_date": "2024-02-01"}, 1)
        relabelled = send(client, "patch", url(person, hire.pk), {"reason": "merit"}, 1)
        removed = send(client, "delete", url(person, hire.pk), None, 1)

        assert (moved.status_code, relabelled.status_code, removed.status_code) == (400, 400, 400)

    def test_a_later_change_can_be_moved_or_removed(self, client: Client) -> None:
        person = employee()
        entry = record(
            person, effective_date=date(2025, 4, 1), amount=Decimal("1926000"), reason="merit"
        )

        moved = send(client, "patch", url(person, entry.pk), {"effective_date": "2025-05-01"}, 1)
        removed = send(client, "delete", url(person, entry.pk), None, 2)

        assert (moved.status_code, removed.status_code) == (200, 200)
        assert removed.json()["employee_version"] == 3
        assert SalaryRecord.objects.filter(employee=person).count() == 1

    def test_a_correction_can_t_become_a_hire(self, client: Client) -> None:
        person = employee()
        entry = record(
            person, effective_date=date(2025, 4, 1), amount=Decimal("1926000"), reason="merit"
        )

        assert (
            send(client, "patch", url(person, entry.pk), {"reason": "hire"}, 1).status_code == 400
        )

    def test_moving_onto_another_change_s_day_is_a_409(self, client: Client) -> None:
        person = employee()
        entry = record(
            person, effective_date=date(2025, 4, 1), amount=Decimal("1926000"), reason="merit"
        )

        response = send(client, "patch", url(person, entry.pk), {"effective_date": "2024-01-15"}, 1)

        assert response.status_code == 409

    def test_someone_else_s_record_is_404(self, client: Client) -> None:
        person, other = employee(), employee()
        theirs = other.salary_records.get()

        assert send(client, "delete", url(person, theirs.pk), None, 1).status_code == 404
