from django.urls import path

from apps.reference import views

urlpatterns = [
    path("countries/", views.CountryList.as_view(), name="country-list"),
    path("departments/", views.DepartmentList.as_view(), name="department-list"),
    path("currencies/", views.CurrencyList.as_view(), name="currency-list"),
]
