"""The employee directory and records (design §7; edge cases #11, #18 to #21)."""

from typing import Any

import pytest
from django.test import Client
from pytest_django import DjangoAssertNumQueries

from apps.reference.models import Country
from tests.factories import department, employee

pytestmark = pytest.mark.django_db

URL = "/api/v1/employees/"
Query = dict[str, str | int | list[str]]


def names(response: Any) -> list[str]:
    return [row["full_name"] for row in response.json()["results"]]


def codes(response: Any) -> list[str]:
    return [row["employee_code"] for row in response.json()["results"]]


class TestPages:
    def test_a_page_has_rows_and_the_total(self, client: Client) -> None:
        for _ in range(5):
            employee()

        body = client.get(URL, {"page": 2, "page_size": 2}).json()

        assert (body["count"], body["page"], body["page_size"]) == (5, 2, 2)
        assert len(body["results"]) == 2

    def test_a_row_shows_the_salary_at_its_currency_decimals(self, client: Client) -> None:
        employee(salary="150000", currency_id="JPY", country=Country.objects.get(code="JP"))

        (row,) = client.get(URL).json()["results"]

        assert (row["salary"], row["currency"]) == ("150000", "JPY")
        assert row["country"] == {"code": "JP", "name": "Japan"}

    def test_a_page_past_the_end_is_empty_but_keeps_the_total(self, client: Client) -> None:
        employee()

        response = client.get(URL, {"page": 9})

        assert response.status_code == 200
        assert (response.json()["count"], response.json()["results"]) == (1, [])

    def test_a_huge_page_size_is_capped(self, client: Client) -> None:
        assert client.get(URL, {"page_size": 100_000}).json()["page_size"] == 200

    @pytest.mark.parametrize("bad", [{"page": 0}, {"page": "two"}, {"page_size": 0}])
    def test_nonsense_page_numbers_are_refused(self, client: Client, bad: dict[str, Any]) -> None:
        assert client.get(URL, bad).status_code == 400

    def test_queries_dont_grow_with_the_page(
        self, client: Client, django_assert_num_queries: DjangoAssertNumQueries
    ) -> None:
        for _ in range(30):
            employee()
        with django_assert_num_queries(2):  # the total and the page (design §10)
            assert len(client.get(URL, {"page_size": 30}).json()["results"]) == 30


class TestSearch:
    def test_accents_and_case_dont_matter(self, client: Client) -> None:
        employee(full_name="José Núñez")
        employee(full_name="Joseph Hill")
        employee(full_name="Ana Silva")

        assert sorted(names(client.get(URL, {"q": "JOSE"}))) == ["Joseph Hill", "José Núñez"]
        assert names(client.get(URL, {"q": "núñez"})) == ["José Núñez"]

    def test_finds_by_employee_code(self, client: Client) -> None:
        wanted = employee(employee_code="QA-0042")
        employee(employee_code="QA-0099")

        assert codes(client.get(URL, {"q": "qa-0042"})) == [wanted.employee_code]

    @pytest.mark.parametrize(("term", "match"), [("ana_m", "Ana_Maria"), ("100%", "100% Sure")])
    def test_like_wildcards_match_literally(self, client: Client, term: str, match: str) -> None:
        for name in ["Ana_Maria", "Ana Maria", "100% Sure", "1000 Ways"]:
            employee(full_name=name)

        assert names(client.get(URL, {"q": term})) == [match]


class TestFilters:
    def test_by_countries_and_departments(self, client: Client) -> None:
        sales = department("Sales")
        employee(full_name="In Sales", department=sales)
        employee(full_name="Us Sales", department=sales, country=Country.objects.get(code="US"))
        employee(full_name="Gb Sales", department=sales, country=Country.objects.get(code="GB"))
        employee(full_name="In Engineering")

        query: Query = {"country": ["IN", "US"], "department": sales.pk}
        response = client.get(URL, query)

        assert sorted(names(response)) == ["In Sales", "Us Sales"]

    def test_a_filter_matching_nobody_is_an_empty_page(self, client: Client) -> None:
        employee()
        response = client.get(URL, {"q": "nobody by this name"})
        assert response.status_code == 200 and response.json()["count"] == 0


class TestSort:
    def test_by_name_by_default(self, client: Client) -> None:
        for name in ["Carla", "ana", "Bruno"]:
            employee(full_name=name)
        assert names(client.get(URL)) == ["ana", "Bruno", "Carla"]

    @pytest.mark.parametrize(
        ("sort", "expected"),
        [("country", ["Germany", "India", "Japan"]), ("-country", ["Japan", "India", "Germany"])],
    )
    def test_by_country_name(self, client: Client, sort: str, expected: list[str]) -> None:
        for code in ["IN", "JP", "DE"]:
            employee(country=Country.objects.get(code=code))

        rows = client.get(URL, {"sort": sort}).json()["results"]

        assert [row["country"]["name"] for row in rows] == expected

    def test_equal_values_keep_their_order_across_pages(self, client: Client) -> None:
        twins = [employee(full_name="Same Name") for _ in range(4)]

        query: Query = {"page_size": 2, "sort": "-full_name"}
        first = client.get(URL, query).json()["results"]
        second = client.get(URL, {**query, "page": 2}).json()["results"]

        seen = [row["id"] for row in [*first, *second]]
        assert seen == [twin.pk for twin in twins]

    @pytest.mark.parametrize("bad", [{"sort": "salary"}, {"sort": "search_text"}, {"order": "x"}])
    def test_only_listed_sorts_and_parameters_are_accepted(
        self, client: Client, bad: dict[str, str]
    ) -> None:
        response = client.get(URL, bad)

        assert response.status_code == 400
        assert set(response.json()["errors"]) == set(bad)


class TestRecord:
    def test_has_every_field_and_its_version_as_an_etag(self, client: Client) -> None:
        person = employee(full_name="Asha Rao", email="asha@acme.example")

        response = client.get(f"{URL}{person.pk}/")

        assert response["ETag"] == '"1"'
        body = response.json()
        assert (body["full_name"], body["email"], body["version"]) == (
            "Asha Rao",
            "asha@acme.example",
            1,
        )
        assert (body["salary"], body["currency"]) == ("1800000.00", "INR")
        assert body["department"]["name"] == "Engineering"

    def test_an_unknown_employee_is_404(self, client: Client) -> None:
        assert client.get(f"{URL}999999/").status_code == 404

    def test_reads_in_one_query(
        self, client: Client, django_assert_num_queries: DjangoAssertNumQueries
    ) -> None:
        person = employee()
        with django_assert_num_queries(1):
            client.get(f"{URL}{person.pk}/")
