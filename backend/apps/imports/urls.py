from django.urls import path

from apps.imports import views

urlpatterns = [
    path("preview/", views.PreviewView.as_view(), name="import-preview"),
    path("apply/", views.ApplyView.as_view(), name="import-apply"),
]
