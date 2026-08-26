from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.landing_page_view, name="landing"),
    path("dashboard/", views.dashboard_home, name="home"),
    path("workspace/", views.dashboard_home, name="dashboard"),
    path("my-work/", views.my_work_view, name="my_work"),
    path("activity/", views.activity_log_view, name="activity"),
    path("search/", views.global_search_view, name="search"),
]
