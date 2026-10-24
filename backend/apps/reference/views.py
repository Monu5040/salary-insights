"""Reference lists for the SPA's filters and forms (design §7)."""

from rest_framework.generics import ListAPIView

from apps.reference.models import Country, Currency, Department
from apps.reference.serializers import (
    CountrySerializer,
    CurrencySerializer,
    DepartmentSerializer,
)


class CountryList(ListAPIView[Country]):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer


class DepartmentList(ListAPIView[Department]):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer


class CurrencyList(ListAPIView[Currency]):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
