"""Deterministic demo data: employees with realistic current salaries (design §12).

A salary is a base for the seniority x a department factor x a country factor x log-normal
noise, converted to local currency at the fixed rates and rounded to a sensible step per
currency. Seniority only shapes the job title and the pay: levels aren't stored. The same seed
gives identical data on every run.

About 1% of people are planted far from their peers, so the peer comparison has something to find.
"""

import math
import random
import unicodedata
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from faker import Faker

from domain.fx import Rates


@dataclass(frozen=True)
class CountryProfile:
    weight: int
    locale: str
    currency: str
    pay_factor: Decimal  # local pay level relative to the US


COUNTRIES = {
    "IN": CountryProfile(35, "en_IN", "INR", Decimal("0.28")),
    "US": CountryProfile(20, "en_US", "USD", Decimal("1.00")),
    "GB": CountryProfile(8, "en_GB", "GBP", Decimal("0.75")),
    "DE": CountryProfile(7, "de_DE", "EUR", Decimal("0.80")),
    "FR": CountryProfile(5, "fr_FR", "EUR", Decimal("0.72")),
    "JP": CountryProfile(6, "ja_JP", "JPY", Decimal("0.65")),
    "SG": CountryProfile(5, "en_US", "SGD", Decimal("0.85")),
    "KW": CountryProfile(3, "ar_AA", "KWD", Decimal("0.70")),
    "BR": CountryProfile(6, "pt_BR", "BRL", Decimal("0.35")),
    "ID": CountryProfile(5, "id_ID", "IDR", Decimal("0.25")),
}

# Department: (weight, role used in job titles, pay factor)
DEPARTMENTS = {
    "Engineering": (30, "Software Engineer", Decimal("1.10")),
    "Product": (8, "Product Manager", Decimal("1.08")),
    "Design": (5, "Product Designer", Decimal("1.00")),
    "Sales": (15, "Account Executive", Decimal("1.00")),
    "Marketing": (7, "Marketing Specialist", Decimal("0.95")),
    "Customer Support": (12, "Support Specialist", Decimal("0.80")),
    "Finance": (6, "Financial Analyst", Decimal("1.00")),
    "Human Resources": (5, "HR Generalist", Decimal("0.92")),
    "Operations": (8, "Operations Analyst", Decimal("0.88")),
    "Legal": (4, "Legal Counsel", Decimal("1.12")),
}

# Seniority: (weight, base annual salary in USD)
LEVELS = {
    "L1": (18, 45_000),
    "L2": (22, 60_000),
    "L3": (24, 80_000),
    "L4": (18, 105_000),
    "L5": (10, 135_000),
    "L6": (6, 170_000),
    "L7": (2, 220_000),
}

TITLE_PATTERNS = {
    "L1": "Associate {role}",
    "L2": "{role}",
    "L3": "{role} II",
    "L4": "Senior {role}",
    "L5": "Lead {role}",
    "L6": "Principal {role}",
    "L7": "Director, {department}",
}

# Salaries are rounded to a step that looks like a real offer in each currency.
SALARY_STEPS = {
    "USD": Decimal(500),
    "INR": Decimal(1000),
    "GBP": Decimal(500),
    "EUR": Decimal(500),
    "JPY": Decimal(10_000),
    "SGD": Decimal(500),
    "KWD": Decimal(10),
    "BRL": Decimal(500),
    "IDR": Decimal(1_000_000),
}

# The fixed budget rates, USD per unit, as in the reference data migration.
FX_RATES = {
    "USD": Decimal("1"),
    "INR": Decimal("0.0115"),
    "GBP": Decimal("1.27"),
    "EUR": Decimal("1.08"),
    "JPY": Decimal("0.0067"),
    "SGD": Decimal("0.75"),
    "KWD": Decimal("3.26"),
    "BRL": Decimal("0.18"),
    "IDR": Decimal("0.000061"),
}

FIRST_HIRE = date(2015, 1, 1)
FAMILY_NAME_FIRST = {"ja_JP"}


@dataclass(frozen=True)
class SeedEmployee:
    code: str
    full_name: str
    email: str
    country: str
    department: str
    job_title: str
    hire_date: date
    salary: Decimal
    currency: str


def generate(count: int, seed: int, as_of: date) -> list[SeedEmployee]:
    """Generate `count` employees as of a date. Same arguments, same data."""
    return _Generator(seed, as_of).employees(count)


class _Generator:
    def __init__(self, seed: int, as_of: date) -> None:
        self.rng = random.Random(seed)  # noqa: S311  (deterministic demo data, not security)
        self.as_of = as_of
        self.rates = Rates(FX_RATES)
        self.fakers: dict[str, Faker] = {}
        for index, locale in enumerate(sorted({c.locale for c in COUNTRIES.values()})):
            self.fakers[locale] = Faker(locale)
            self.fakers[locale].seed_instance(seed + index)

    def employees(self, count: int) -> list[SeedEmployee]:
        return [self.employee(number) for number in range(1, count + 1)]

    def pick(self, weights: dict[str, int]) -> str:
        return self.rng.choices(list(weights), weights=list(weights.values()))[0]

    def employee(self, number: int) -> SeedEmployee:
        code = f"E{number:05d}"
        country = self.pick({key: profile.weight for key, profile in COUNTRIES.items()})
        department = self.pick({key: value[0] for key, value in DEPARTMENTS.items()})
        level = self.pick({key: value[0] for key, value in LEVELS.items()})
        role = DEPARTMENTS[department][1]
        currency = COUNTRIES[country].currency
        return SeedEmployee(
            code=code,
            full_name=self.name(COUNTRIES[country].locale),
            email=f"{code.lower()}@acme.example",
            country=country,
            department=department,
            job_title=TITLE_PATTERNS[level].format(role=role, department=department),
            hire_date=self.hire_date(),
            salary=self.salary(country, department, level),
            currency=currency,
        )

    def name(self, locale: str) -> str:
        fake = self.fakers[locale]
        first, last = fake.first_name(), fake.last_name()
        full = f"{last} {first}" if locale in FAMILY_NAME_FIRST else f"{first} {last}"
        return unicodedata.normalize("NFC", full)

    def hire_date(self) -> date:
        span = (self.as_of - FIRST_HIRE).days - 30
        return FIRST_HIRE + timedelta(days=int(self.rng.triangular(0, span, span)))

    def salary(self, country: str, department: str, level: str) -> Decimal:
        usd = Decimal(LEVELS[level][1]) * DEPARTMENTS[department][2] * self.noise()
        if self.rng.random() < 0.01:  # planted outlier
            usd *= self.rng.choice([Decimal("0.65"), Decimal("1.45")])
        profile = COUNTRIES[country]
        local = usd * profile.pay_factor / self.rates.usd_per_unit(profile.currency)
        return self.round(local, profile.currency)

    def noise(self) -> Decimal:
        return Decimal(str(round(math.exp(self.rng.gauss(0, 0.12)), 4)))

    @staticmethod
    def round(amount: Decimal, currency: str) -> Decimal:
        step = SALARY_STEPS[currency]
        return (amount / step).quantize(Decimal(1), rounding=ROUND_HALF_UP) * step
