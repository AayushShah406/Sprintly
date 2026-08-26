from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("sprint-health/", views.SprintHealthView.as_view(), name="sprint_health_active"),
    path("sprint-health/<int:sprint_id>/", views.SprintHealthView.as_view(), name="sprint_health_detail"),
    path("overview/", views.AnalyticsOverviewView.as_view(), name="overview"),
    path("historical/<int:sprint_id>/", views.HistoricalHealthLogsView.as_view(), name="historical"),
]
