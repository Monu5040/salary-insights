"""Insights on a small hand-computed company (design §4; edge cases #4, #22, #24).

In USD at the fixed rates from the reference data (INR at 0.0115 USD):

 who   country department  title            salary         USD
 Ana   IN      Engineering Data Analyst     ₹20,00,000     23,000
 Bea   IN      Engineering Data Analyst     ₹40,00,000     46,000
 Carl  IN      Sales       Account Manager  ₹60,00,000     69,000
 Gus   IN      Sales       Account Manager  $30,000        30,000  (paid in USD)
 Hana  US      Engineering Data Analyst     $90,000        90,000
 Ivan  US      Sales       Account Manager  $100,000      100,000

Payroll 358,000; median (46,000 + 69,000) / 2 = 57,500; mean 59,666.67. Everyone was hired on
15 Jan 2024; Ana has a raise to ₹22,00,000 agreed from 1 Oct 2026, after today (30 Sep 2026).
"""

import json
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.test import Client
from pytest_django import DjangoAssertNumQueries
from pytest_django.fixtures import Settings

from apps.analytics import questions
from apps.analytics.presets import PRESETS
from apps.analytics.serializers import ExploreQuery
from apps.employees.models import Employee
from apps.reference.models import Country
from tests.factories import department, employee, record

pytestmark = pytest.mark.django_db

URL = "/api/v1/analytics/"
FX_BASIS = "Converted through USD at fixed budget exchange rates"


@pytest.fixture
def company(today: date) -> dict[str, Employee]:
    us = Country.objects.get(code="US")
    sales = department("Sales")
    analyst: dict[str, Any] = {"job_title": "Data Analyst"}
    manager: dict[str, Any] = {"job_title": "Account Manager", "department": sales}
    dollars: dict[str, Any] = {"currency_id": "USD"}
    people = [
        employee(full_name="Ana", salary=Decimal("2000000"), **analyst),
        employee(full_name="Bea", salary=Decimal("4000000"), **analyst),
        employee(full_name="Carl", salary=Decimal("6000000"), **manager),
        employee(full_name="Gus", salary=Decimal("30000"), **dollars, **manager),
        employee(full_name="Hana", salary=Decimal("90000"), country=us, **dollars, **analyst),
        employee(full_name="Ivan", salary=Decimal("100000"), country=us, **dollars, **manager),
    ]
    record(people[0], effective_date=date(2026, 10, 1), amount=Decimal("2200000"), reason="merit")
    return {who.full_name: who for who in people}


def get(client: Client, path: str, **params: Any) -> Any:
    response = client.get(URL + path, params)
    assert response.status_code == 200, response.content
    return response.json()


class TestSummary:
    def test_headcount_payroll_median_and_mean(
        self, client: Client, company: dict[str, Employee]
    ) -> None:
        assert get(client, "summary/") == {
            "as_of": "2026-09-30",
            "currency": "USD",
            "fx_basis": FX_BASIS,
            "headcount": 6,
            "payroll": "358000.00",
            "median": "57500.00",
            "mean": "59666.67",
        }

    def test_on_another_day_with_the_salaries_in_force_then(
        self, client: Client, company: dict[str, Employee]
    ) -> None:
        later = get(client, "summary/", as_of="2026-10-01")
        before_anyone = get(client, "summary/", as_of="2024-01-14")

        assert later["payroll"] == "360300.00"  # Ana's raise: + ₹2,00,000 = $2,300
        assert (before_anyone["headcount"], before_anyone["median"]) == (0, None)

    def test_in_another_currency(self, client: Client, company: dict[str, Employee]) -> None:
        body = get(client, "summary/", currency="INR")

        assert (body["currency"], body["payroll"]) == ("INR", "31130434.78")

    def test_an_unknown_currency_has_no_answer(
        self, client: Client, company: dict[str, Employee]
    ) -> None:
        response = client.get(URL + "summary/", {"currency": "XYZ"})

        assert response.status_code == 422
        assert response.json()["detail"] == "No exchange rate for XYZ."

    def test_filters_by_country_and_department(
        self, client: Client, company: dict[str, Employee]
    ) -> None:
        sales = company["Carl"].department_id
        body = get(client, "summary/", country="IN", department=sales)

        assert (body["headcount"], body["payroll"]) == (2, "99000.00")  # Carl and Gus

    def test_nobody_in_scope_has_no_statistics(
        self, client: Client, company: dict[str, Employee]
    ) -> None:
        body = get(client, "summary/", country="JP")

        assert (body["headcount"], body["payroll"], body["median"], body["mean"]) == (
            0,
            "0.00",
            None,
            None,
        )

    def test_answers_in_two_queries(
        self,
        client: Client,
        company: dict[str, Employee],
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        with django_assert_num_queries(2):  # the currency, then the numbers
            get(client, "summary/")


class TestExplore:
    def test_payroll_by_country(self, client: Client, company: dict[str, Employee]) -> None:
        body = get(client, "explore/", metric="payroll", by="country")
        groups = body["groups"]

        rows = [(g["labels"]["country"], g["headcount"], g["values"]["payroll"]) for g in groups]
        assert rows == [("India", 4, "168000.00"), ("United States", 2, "190000.00")]
        assert (body["currency"], body["fx_basis"]) == ("USD", FX_BASIS)

    def test_ranges_by_job_title(self, client: Client, company: dict[str, Employee]) -> None:
        body = get(client, "explore/", metric=["min", "median", "max"], by="title")

        analysts = next(g for g in body["groups"] if g["keys"]["title"] == "Data Analyst")
        assert analysts["values"] == {"min": "23000.00", "median": "46000.00", "max": "90000.00"}

    def test_two_dimensions_at_once(self, client: Client, company: dict[str, Employee]) -> None:
        body = get(client, "explore/", metric="headcount", by=["country", "department"])

        cells = {
            (g["labels"]["country"], g["labels"]["department"]): g["values"]["headcount"]
            for g in body["groups"]
        }
        assert cells == {
            ("India", "Engineering"): "2",
            ("India", "Sales"): "2",
            ("United States", "Engineering"): "1",
            ("United States", "Sales"): "1",
        }

    def test_groups_by_tenure_on_the_organizations_today(
        self, client: Client, company: dict[str, Employee]
    ) -> None:
        body = get(client, "explore/", metric="headcount", by="tenure")

        # Everyone was hired on 15 Jan 2024; today is 30 Sep 2026.
        assert [g["labels"]["tenure"] for g in body["groups"]] == ["1 to 2 years"]

    def test_flags_groups_too_small_to_read_much_into(
        self, client: Client, company: dict[str, Employee], settings: Settings
    ) -> None:
        settings.MIN_GROUP_SIZE = 3
        body = get(client, "explore/", metric="median", by="country")

        assert [(g["keys"]["country"], g["low_sample"]) for g in body["groups"]] == [
            ("IN", False),
            ("US", True),
        ]

    @pytest.mark.parametrize(
        "bad",
        [
            {"metric": "salary_sum"},
            {"metric": "median", "by": "gender"},
            {"metric": "median", "by": ["country", "country"]},
            {"metric": "median", "by": ["country", "department", "title"]},
            {"by": "country"},
            {"metric": "median", "as_of": "next week"},
        ],
    )
    def test_only_listed_metrics_and_dimensions_reach_the_sql(
        self, client: Client, bad: dict[str, Any]
    ) -> None:
        assert client.get(URL + "explore/", bad).status_code == 400


class TestPresets:
    def test_the_dashboard_questions_are_valid_explorer_queries(self, client: Client) -> None:
        presets = get(client, "presets/")

        assert [preset["id"] for preset in presets] == [preset["id"] for preset in PRESETS]
        for preset in presets:
            query = ExploreQuery(data={"metric": preset["metrics"], "by": preset["by"]})
            assert query.is_valid(), query.errors


class TestPeers:
    def test_compares_with_the_same_job_title_in_the_same_country(
        self, client: Client, company: dict[str, Employee], settings: Settings
    ) -> None:
        settings.MIN_GROUP_SIZE = 1
        body = client.get(f"/api/v1/employees/{company['Ana'].pk}/peers/").json()

        assert body == {
            "currency": "INR",
            "definition": "Same job title and country",
            "peers": 1,  # Bea: Ana isn't her own peer
            "low_sample": False,
            "pay": "2000000.00",
            "p10": "4000000.00",
            "p25": "4000000.00",
            "median": "4000000.00",
            "p75": "4000000.00",
            "p90": "4000000.00",
            "percentile_rank": "0",
            "compa_ratio": "0.50",
        }

    def test_widens_to_every_country_when_the_group_is_too_small(
        self, client: Client, company: dict[str, Employee]
    ) -> None:
        body = client.get(f"/api/v1/employees/{company['Ana'].pk}/peers/").json()

        # Bea and Hana, whose $90,000 is ₹78,26,086.96 at the fixed rates.
        assert (body["definition"], body["peers"], body["low_sample"]) == (
            "Same job title, every country",
            2,
            True,
        )
        assert (body["median"], body["compa_ratio"]) == ("5913043.48", "0.34")

    def test_compares_in_the_currency_of_the_employees_country(
        self, client: Client, company: dict[str, Employee]
    ) -> None:
        body = client.get(f"/api/v1/employees/{company['Gus'].pk}/peers/").json()

        assert (body["currency"], body["pay"]) == ("INR", "2608695.65")  # $30,000

    def test_someone_with_a_unique_title_has_no_peers(self, client: Client, today: date) -> None:
        loner = employee(job_title="Chief Everything Officer")

        body = client.get(f"/api/v1/employees/{loner.pk}/peers/").json()

        assert (body["peers"], body["median"], body["compa_ratio"]) == (0, None, None)
        assert body["percentile_rank"] is None

    def test_reads_in_a_fixed_number_of_queries(
        self,
        client: Client,
        company: dict[str, Employee],
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        with django_assert_num_queries(3):  # the employee, the rates, the colleagues
            client.get(f"/api/v1/employees/{company['Ana'].pk}/peers/")


class TestPayEquity:
    def test_lists_people_far_from_others_in_the_same_role(
        self, client: Client, company: dict[str, Employee], settings: Settings
    ) -> None:
        settings.MIN_GROUP_SIZE = 2
        body = get(client, "pay-equity/")

        # Too few share a country, so everyone is compared with their whole job title.
        # Analysts: Hana $90,000 against Ana and Bea's median, $34,500: 2.61; Ana $23,000
        # against $68,000: 0.34; Bea is 0.81. Managers: Ivan $100,000 against $49,500: 2.02;
        # Gus $30,000 against $84,500: 0.36; Carl is 1.06. Furthest from 1 first.
        names = [(row["full_name"], row["compa_ratio"]) for row in body["results"]]
        assert names == [("Hana", "2.61"), ("Ivan", "2.02"), ("Ana", "0.34"), ("Gus", "0.36")]
        assert (body["band"], body["count"]) == (["0.80", "1.20"], 4)

    def test_needs_enough_peers_to_call_anyone_an_outlier(
        self, client: Client, company: dict[str, Employee]
    ) -> None:
        assert get(client, "pay-equity/")["count"] == 0  # groups of 2 and 3 are under 5


class TestQuestions:
    def ask(self, client: Client, question: str = "Payroll by country?") -> Any:
        return client.post(URL + "ask/", {"question": question}, content_type="application/json")

    def test_turns_a_question_into_an_explorer_answer(
        self,
        client: Client,
        company: dict[str, Employee],
        settings: Settings,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        settings.GROQ_API_KEY = "test-key"
        sent: list[str] = []

        def reply(system: str, question: str) -> str:
            sent.append(system + question)
            reading = {
                "metric": ["payroll"],
                "by": ["country"],
                "country": [],
                "department": [],
                "currency": None,
                "as_of": None,
                "summary": "Payroll by country, in USD.",
                "understood": True,
            }
            return json.dumps(reading)

        monkeypatch.setattr(questions, "_chat", reply)

        body = self.ask(client).json()

        assert body["summary"] == "Payroll by country, in USD."
        assert body["query"] == {
            "metric": ["payroll"],
            "by": ["country"],
            "country": [],
            "department": [],
        }
        rows = [(g["labels"]["country"], g["values"]["payroll"]) for g in body["answer"]["groups"]]
        assert rows == [("India", "168000.00"), ("United States", "190000.00")]
        assert "IN=India" in sent[0] and "1800000" not in sent[0]  # no salaries leave

    @pytest.mark.parametrize(
        "reading",
        [
            {"metric": ["salary_sum"]},
            {"metric": ["median"], "by": ["gender"]},
            {"metric": ["median"], "by": ["country", "country"]},
            {"understood": False},
        ],
    )
    def test_anything_outside_the_allow_lists_is_refused(
        self,
        client: Client,
        settings: Settings,
        monkeypatch: pytest.MonkeyPatch,
        reading: dict[str, Any],
    ) -> None:
        settings.GROQ_API_KEY = "test-key"
        monkeypatch.setattr(questions, "_chat", lambda system, question: json.dumps(reading))

        assert self.ask(client).status_code == 422

    def test_without_a_key_it_says_so(self, client: Client, settings: Settings) -> None:
        settings.GROQ_API_KEY = ""

        response = self.ask(client)

        assert response.status_code == 503
        assert "no Groq key" in response.json()["detail"]

    def test_a_reply_that_isnt_json_is_a_503(
        self, client: Client, settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        settings.GROQ_API_KEY = "test-key"
        monkeypatch.setattr(questions, "_chat", lambda system, question: "Sure! Here you go")

        assert self.ask(client).status_code == 503

    def test_a_long_question_is_refused(self, client: Client) -> None:
        assert self.ask(client, "x" * 301).status_code == 400
