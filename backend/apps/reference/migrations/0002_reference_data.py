"""Reference data every environment needs: currencies with fixed budget rates, countries and
departments.

Currencies cover the awkward cases on purpose: JPY has no minor unit, KWD has three, and IDR has
huge nominal amounts. USD is 1, so the reporting currency always has a rate (design §3).
"""

from decimal import Decimal

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

CURRENCIES = [
    # code, name, minor units, annual salary ceiling, fixed budget rate in USD per unit
    ("USD", "US Dollar", 2, "5000000", "1"),
    ("INR", "Indian Rupee", 2, "300000000", "0.0115"),
    ("GBP", "Pound Sterling", 2, "4000000", "1.27"),
    ("EUR", "Euro", 2, "4500000", "1.08"),
    ("JPY", "Japanese Yen", 0, "700000000", "0.0067"),
    ("SGD", "Singapore Dollar", 2, "7000000", "0.75"),
    ("KWD", "Kuwaiti Dinar", 3, "1500000", "3.26"),
    ("BRL", "Brazilian Real", 2, "25000000", "0.18"),
    ("IDR", "Indonesian Rupiah", 2, "80000000000", "0.000061"),
]

COUNTRIES = [
    # code, name, default currency, locale
    ("IN", "India", "INR", "en-IN"),
    ("US", "United States", "USD", "en-US"),
    ("GB", "United Kingdom", "GBP", "en-GB"),
    ("DE", "Germany", "EUR", "de-DE"),
    ("FR", "France", "EUR", "fr-FR"),
    ("JP", "Japan", "JPY", "ja-JP"),
    ("SG", "Singapore", "SGD", "en-SG"),
    ("KW", "Kuwait", "KWD", "ar-KW"),
    ("BR", "Brazil", "BRL", "pt-BR"),
    ("ID", "Indonesia", "IDR", "id-ID"),
]

DEPARTMENTS = [
    "Customer Support",
    "Design",
    "Engineering",
    "Finance",
    "Human Resources",
    "Legal",
    "Marketing",
    "Operations",
    "Product",
    "Sales",
]


def load(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Currency = apps.get_model("reference", "Currency")
    Country = apps.get_model("reference", "Country")
    Department = apps.get_model("reference", "Department")

    Currency.objects.bulk_create(
        Currency(
            code=code,
            name=name,
            minor_units=minor,
            salary_ceiling=Decimal(ceiling),
            usd_per_unit=Decimal(rate),
        )
        for code, name, minor, ceiling, rate in CURRENCIES
    )
    Country.objects.bulk_create(
        Country(code=code, name=name, default_currency_id=currency, locale=locale)
        for code, name, currency, locale in COUNTRIES
    )
    Department.objects.bulk_create(Department(name=name) for name in DEPARTMENTS)


def unload(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    for model in ("Department", "Country", "Currency"):
        apps.get_model("reference", model).objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("reference", "0001_initial")]
    operations = [migrations.RunPython(load, unload)]
