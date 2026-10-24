"""Reference data: currencies with their fixed exchange rates, countries and departments.

Loaded by migrations, so every environment has the same lists. Rules live in the database,
not only in forms (design §3).
"""

from django.db import models
from django.db.models import CheckConstraint, Q


class Currency(models.Model):
    code = models.CharField(primary_key=True, max_length=3, help_text="ISO 4217, e.g. INR")
    name = models.CharField(max_length=64)
    minor_units = models.PositiveSmallIntegerField(
        help_text="Digits after the decimal point: 0 for JPY, 2 for USD, 3 for KWD"
    )
    salary_ceiling = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        help_text="Annual salaries above this are rejected as likely typos (extra zeros)",
    )
    usd_per_unit = models.DecimalField(
        max_digits=20,
        decimal_places=10,
        help_text="Fixed budget exchange rate: USD for one unit of this currency",
    )

    class Meta:
        db_table = "currencies"
        ordering = ["code"]
        verbose_name_plural = "currencies"
        constraints = [
            CheckConstraint(condition=Q(code__regex=r"^[A-Z]{3}$"), name="currency_code_is_iso"),
            CheckConstraint(condition=Q(minor_units__lte=4), name="currency_minor_units_fit"),
            CheckConstraint(condition=Q(salary_ceiling__gt=0), name="currency_ceiling_positive"),
            CheckConstraint(condition=Q(usd_per_unit__gt=0), name="currency_rate_positive"),
        ]

    def __str__(self) -> str:
        return self.code


class Country(models.Model):
    code = models.CharField(primary_key=True, max_length=2, help_text="ISO 3166, e.g. IN")
    name = models.CharField(max_length=100, unique=True)
    default_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="+")
    locale = models.CharField(max_length=10, help_text="Formats money in the UI, e.g. en-IN")

    class Meta:
        db_table = "countries"
        ordering = ["name"]
        verbose_name_plural = "countries"
        constraints = [
            CheckConstraint(condition=Q(code__regex=r"^[A-Z]{2}$"), name="country_code_is_iso"),
        ]

    def __str__(self) -> str:
        return self.name


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "departments"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
