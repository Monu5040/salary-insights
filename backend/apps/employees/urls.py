from django.urls import path

from apps.employees.views import EmployeeViewSet

urlpatterns = [
    path("", EmployeeViewSet.as_view({"get": "list"}), name="employee-list"),
    path(
        "<int:pk>/",
        EmployeeViewSet.as_view({"get": "retrieve"}),
        name="employee-detail",
    ),
]
