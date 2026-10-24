"""Load deterministic demo employees with their current salaries (design §12)."""

import time
from argparse import ArgumentParser
from datetime import date
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from apps.employees import seeding
from apps.employees.models import Employee
from apps.reference.models import Country, Department
from domain.text import fold

# The public demo resets itself every night with this command (design §10).
ALLOWED_ENVIRONMENTS = {"dev", "test", "demo"}


class Command(BaseCommand):
    help = "Load deterministic demo employees. Never runs in production."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--employees", type=int, default=10_000)
        parser.add_argument("--seed", type=int, default=42, help="Same seed, same data")
        parser.add_argument(
            "--as-of", type=date.fromisoformat, default=date(2026, 9, 30), help="YYYY-MM-DD"
        )
        parser.add_argument("--reset", action="store_true", help="Replace existing employees")

    def handle(self, *args: Any, **options: Any) -> None:
        if settings.ENVIRONMENT not in ALLOWED_ENVIRONMENTS:
            raise CommandError(
                f"The seed runs only in {', '.join(sorted(ALLOWED_ENVIRONMENTS))}; "
                f"this environment is {settings.ENVIRONMENT!r}."
            )
        started = time.perf_counter()
        with transaction.atomic():
            if Employee.objects.exists():
                if not options["reset"]:
                    raise CommandError("Employees already exist. Run with --reset to replace them.")
                with connection.cursor() as cursor:
                    cursor.execute("TRUNCATE employees RESTART IDENTITY")
            people = seeding.generate(options["employees"], options["seed"], options["as_of"])
            self.insert(people)
        with connection.cursor() as cursor:
            cursor.execute("ANALYZE employees")  # planner stats after a bulk load
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(people):,} employees in {time.perf_counter() - started:.1f}s."
            )
        )

    def insert(self, people: list[seeding.SeedEmployee]) -> None:
        departments = dict(Department.objects.values_list("name", "pk"))
        countries = set(Country.objects.values_list("code", flat=True))
        missing = {person.country for person in people} - countries
        missing |= {person.department for person in people} - set(departments)
        if missing:
            raise CommandError(f"Unknown reference data {sorted(missing)}: run the migrations.")
        Employee.objects.bulk_create(
            [
                Employee(
                    employee_code=person.code,
                    full_name=person.full_name,
                    email=person.email,
                    country_id=person.country,
                    department_id=departments[person.department],
                    job_title=person.job_title,
                    hire_date=person.hire_date,
                    salary=person.salary,
                    currency_id=person.currency,
                    search_text=fold(f"{person.full_name} {person.code}"),
                )
                for person in people
            ],
            batch_size=2000,
        )
