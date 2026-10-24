from rest_framework import serializers

from apps.reference.models import Country, Currency, Department


class CountrySerializer(serializers.ModelSerializer[Country]):
    class Meta:
        model = Country
        fields = ["code", "name", "default_currency", "locale"]


class DepartmentSerializer(serializers.ModelSerializer[Department]):
    class Meta:
        model = Department
        fields = ["id", "name"]


class CurrencySerializer(serializers.ModelSerializer[Currency]):
    class Meta:
        model = Currency
        fields = ["code", "name", "minor_units", "usd_per_unit"]
