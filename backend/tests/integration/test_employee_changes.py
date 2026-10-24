"""Adding, editing and removing employees, salary included (design §7; edge cases #7, #8,
#10 to #16)."""

from decimal import Decimal
from typing import Any

import pytest
from django.test import Client

from apps.employees.models import Employee
from tests.factories import department, employee

pytestmark = pytest.mark.django_db

URL = "/api/v1/employees/"


def new(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "employee_code": " e00777 ",
        "full_name": "  José   Núñez ",
        "email": "Jose.Nunez@acme.example",
        "country": "IN",
        "department": department().pk,
        "job_title": "Data Analyst",
        "hire_date": "2026-10-01",
        "salary": "1800000",
        "currency": "INR",
    }
    body.update(overrides)
    return body


def create(client: Client, **overrides: Any) -> Any:
    return client.post(URL, new(**overrides), content_type="application/json")


def patch(
    client: Client, person: Employee, body: dict[str, Any], version: int | None = None
) -> Any:
    headers = {"If-Match": f'"{person.version if version is None else version}"'}
    return client.patch(
        f"{URL}{person.pk}/", body, content_type="application/json", headers=headers
    )


def delete(client: Client, person: Employee, version: int | None = None) -> Any:
    headers = {"If-Match": f'"{person.version if version is None else version}"'}
    return client.delete(f"{URL}{person.pk}/", headers=headers)


class TestAdd:
    def test_saves_the_employee_with_their_salary(self, client: Client) -> None:
        response = create(client)

        assert response.status_code == 201
        body = response.json()
        assert (body["employee_code"], body["full_name"]) == ("E00777", "José Núñez")
        assert (body["salary"], body["currency"], body["version"]) == ("1800000.00", "INR", 1)
        assert response["ETag"] == '"1"'
        person = Employee.objects.get(pk=body["id"])
        assert (person.salary, person.currency_id) == (Decimal("1800000"), "INR")

    def test_a_new_employee_can_be_found_straight_away(self, client: Client) -> None:
        create(client)
        assert client.get(URL, {"q": "jose nunez"}).json()["count"] == 1

    def test_can_be_paid_in_another_currency_than_their_country(self, client: Client) -> None:
        response = create(client, salary="95000", currency="USD")
        assert (response.json()["country"]["code"], response.json()["currency"]) == ("IN", "USD")

    @pytest.mark.parametrize(
        ("salary", "currency", "message"),
        [
            ("150000.5", "JPY", "at most 0 decimal places"),
            (1800000, "INR", "as a string"),
            ("1,800,000", "INR", "plain number"),
            ("-5", "INR", "plain number"),
            ("0", "INR", "more than zero"),
            ("99999999999999", "INR", "extra zeros"),
        ],
    )
    def test_the_salary_must_fit_its_currency(
        self, client: Client, salary: Any, currency: str, message: str
    ) -> None:
        response = create(client, salary=salary, currency=currency)

        assert response.status_code == 400
        assert message in response.json()["errors"]["salary"][0]

    @pytest.mark.parametrize(
        "field",
        [{"country": "XX"}, {"department": 999999}, {"currency": "XYZ"}, {"salary": None}],
    )
    def test_unknown_references_are_field_errors(
        self, client: Client, field: dict[str, Any]
    ) -> None:
        response = create(client, **field)

        assert response.status_code == 400
        assert set(response.json()["errors"]) == set(field)

    @pytest.mark.parametrize(
        "field",
        [
            {"full_name": "   "},
            {"full_name": "x" * 201},
            {"employee_code": "E 42"},
            {"employee_code": "=1+1"},
            {"email": "not-an-email"},
            {"job_title": ""},
            {"hire_date": "31/12/2026"},
        ],
    )
    def test_blank_overlong_and_odd_values_are_refused(
        self, client: Client, field: dict[str, Any]
    ) -> None:
        response = create(client, **field)

        assert response.status_code == 400
        assert set(response.json()["errors"]) == set(field)

    def test_a_code_in_use_is_a_409_pointing_at_its_holder(self, client: Client) -> None:
        holder = employee(employee_code="E00777")

        response = create(client, employee_code=" e00777")  # case and spaces don't matter

        assert response.status_code == 409
        body = response.json()
        assert (list(body["errors"]), body["existing_id"]) == (["employee_code"], holder.pk)

    def test_an_email_in_use_in_any_case_is_a_409(self, client: Client) -> None:
        holder = employee(email="jose.nunez@acme.example")

        response = create(client)

        assert response.status_code == 409
        assert (list(response.json()["errors"]), response.json()["existing_id"]) == (
            ["email"],
            holder.pk,
        )

    def test_saving_twice_doesnt_make_a_duplicate(self, client: Client) -> None:
        first = create(client)
        again = create(client)

        assert again.status_code == 409
        assert again.json()["existing_id"] == first.json()["id"]
        assert Employee.objects.count() == 1

    def test_fields_the_server_owns_are_ignored(self, client: Client) -> None:
        response = create(client, id=4242, version=99, search_text="hacked")

        person = Employee.objects.get(pk=response.json()["id"])
        assert (person.pk == 4242, person.version) == (False, 1)
        assert person.search_text == "jose nunez e00777"


class TestEdit:
    def test_a_raise_bumps_the_version(self, client: Client) -> None:
        person = employee()

        response = patch(client, person, {"salary": "1950000"})

        assert response.status_code == 200
        assert (response.json()["salary"], response.json()["version"]) == ("1950000.00", 2)
        assert response["ETag"] == '"2"'

    def test_a_new_currency_is_checked_against_the_salary_on_record(self, client: Client) -> None:
        person = employee(salary=Decimal("1800000.50"))

        response = patch(client, person, {"currency": "JPY"})

        assert response.status_code == 400
        assert "at most 0 decimal places" in response.json()["errors"]["salary"][0]

    def test_a_stale_version_is_refused_and_nothing_changes(self, client: Client) -> None:
        person = employee()
        patch(client, person, {"job_title": "Staff Engineer"})

        response = patch(client, person, {"salary": "1"}, version=1)

        assert response.status_code == 412
        assert response.json()["current_version"] == 2
        person.refresh_from_db()
        assert person.salary == Decimal("1800000")

    def test_a_write_without_if_match_is_refused(self, client: Client) -> None:
        person = employee()

        response = client.patch(f"{URL}{person.pk}/", {}, content_type="application/json")

        assert response.status_code == 428

    def test_saving_without_changes_keeps_the_version(self, client: Client) -> None:
        person = employee()

        response = patch(client, person, {"job_title": person.job_title, "salary": "1800000"})

        assert response.json()["version"] == 1

    def test_a_new_name_is_searchable(self, client: Client) -> None:
        person = employee(full_name="Old Name")

        patch(client, person, {"full_name": "Zoë Quinn"})

        assert client.get(URL, {"q": "zoe"}).json()["count"] == 1

    def test_an_email_in_use_is_a_409(self, client: Client) -> None:
        employee(email="taken@acme.example")
        person = employee()

        response = patch(client, person, {"email": "TAKEN@acme.example"})

        assert response.status_code == 409 and list(response.json()["errors"]) == ["email"]

    def test_an_unknown_employee_is_404(self, client: Client) -> None:
        response = client.patch(
            f"{URL}999999/", {}, content_type="application/json", headers={"If-Match": '"1"'}
        )
        assert response.status_code == 404


class TestDelete:
    def test_removes_the_employee(self, client: Client) -> None:
        person = employee()

        assert delete(client, person).status_code == 204
        assert not Employee.objects.exists()

    def test_a_stale_version_is_refused(self, client: Client) -> None:
        person = employee()
        patch(client, person, {"job_title": "Staff Engineer"})

        assert delete(client, person, version=1).status_code == 412
        assert Employee.objects.exists()

    def test_needs_if_match(self, client: Client) -> None:
        person = employee()
        assert client.delete(f"{URL}{person.pk}/").status_code == 428
