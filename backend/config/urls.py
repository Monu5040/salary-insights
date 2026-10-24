from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerSplitView

from apps.core.views import ConfigView

urlpatterns = [
    path("", include("apps.core.urls")),
    path("api/v1/config/", ConfigView.as_view(), name="config"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # The split view loads its start-up script from a URL, so the docs need no inline script.
    path("api/docs/", SpectacularSwaggerSplitView.as_view(url_name="schema"), name="docs"),
]
