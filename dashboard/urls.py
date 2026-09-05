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
    
    # Global Agile Hub Routes (Support both existing and 0-project users)
    path("board/", views.global_workspace_tab_view, {"tab": "board"}, name="board"),
    path("backlog/", views.global_workspace_tab_view, {"tab": "backlog"}, name="backlog"),
    path("sprints/", views.global_workspace_tab_view, {"tab": "sprints"}, name="sprints"),
    path("roadmap/", views.global_workspace_tab_view, {"tab": "roadmap"}, name="roadmap"),
    path("reports/", views.global_workspace_tab_view, {"tab": "reports"}, name="reports"),
    path("team/", views.global_workspace_tab_view, {"tab": "team"}, name="team"),
]
