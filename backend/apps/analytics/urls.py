from django.urls import path

from apps.analytics import views

urlpatterns = [
    path("summary/", views.SummaryView.as_view(), name="insights-summary"),
    path("explore/", views.ExploreView.as_view(), name="insights-explore"),
    path("presets/", views.PresetsView.as_view(), name="insights-presets"),
]
