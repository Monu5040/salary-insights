from django.urls import path

from apps.compensation.views import SalaryViewSet

# Under /api/v1/employees/<pk>/: a salary history belongs to its employee.
urlpatterns = [
    path("salaries/", SalaryViewSet.as_view({"get": "list", "post": "create"}), name="salary-list"),
    path(
        "salaries/<int:sid>/",
        SalaryViewSet.as_view({"patch": "partial_update", "delete": "destroy"}),
        name="salary-detail",
    ),
]
