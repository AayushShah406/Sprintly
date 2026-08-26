from django.urls import path
from . import views

app_name = "events_engine"

urlpatterns = [
    path("telemetry/", views.ScalabilityTelemetryView.as_view(), name="telemetry"),
    path("simulate/", views.SimulateEventView.as_view(), name="simulate"),
]
