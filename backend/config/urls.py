from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerSplitView

from apps.core.views import ConfigView

# Errors Django answers itself are problem+json under /api/ (edge case #32).
handler404 = "apps.core.errors.page_not_found"
handler500 = "apps.core.errors.server_error"

urlpatterns = [
    path("", include("apps.core.urls")),
    path("api/v1/analytics/", include("apps.analytics.urls")),
    path("api/v1/config/", ConfigView.as_view(), name="config"),
    path("api/v1/employees/", include("apps.employees.urls")),
    path("api/v1/reference/", include("apps.reference.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # The split view loads its start-up script from a URL, so the docs need no inline script.
    path("api/docs/", SpectacularSwaggerSplitView.as_view(url_name="schema"), name="docs"),
]
