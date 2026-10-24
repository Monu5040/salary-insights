from django.urls import path

from apps.employees.views import EmployeeViewSet

urlpatterns = [
    path("", EmployeeViewSet.as_view({"get": "list", "post": "create"}), name="employee-list"),
    path(
        "<int:pk>/",
        EmployeeViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="employee-detail",
    ),
]
