"""Include the optional appointment routes when enabling them inside a test."""

from django.urls import include
from django.urls import path

from sportfac.urls import urlpatterns as project_patterns


urlpatterns = list(project_patterns)
if not any(getattr(pattern, "namespace", None) == "appointments" for pattern in urlpatterns):
    urlpatterns.append(path("rendez-vous/", include("appointments.urls", namespace="appointments")))
