from django.urls import path
from . import views

app_name = "projects"

urlpatterns = [
    path("", views.project_list_view, name="list"),
    path("<int:pk>/", views.project_detail_hub, name="detail"),
    path("<int:pk>/overview/", views.project_detail_hub, {"tab": "overview"}, name="overview"),
    path("<int:pk>/board/", views.project_detail_hub, {"tab": "board"}, name="board"),
    path("<int:pk>/backlog/", views.project_detail_hub, {"tab": "backlog"}, name="backlog"),
    path("<int:pk>/sprints/", views.project_detail_hub, {"tab": "sprints"}, name="sprints"),
    path("<int:pk>/roadmap/", views.project_detail_hub, {"tab": "roadmap"}, name="roadmap"),
    path("<int:pk>/roadmap/gantt/", views.ProjectGanttDataAPI.as_view(), name="roadmap_gantt_api"),
    path("api/<int:pk>/roadmap/gantt/", views.ProjectGanttDataAPI.as_view(), name="roadmap_gantt_api_alt"),
    path("<int:pk>/reports/", views.project_detail_hub, {"tab": "reports"}, name="reports"),
    path("<int:pk>/team/", views.project_detail_hub, {"tab": "team"}, name="team"),
    path("<int:pk>/activity/", views.project_detail_hub, {"tab": "activity"}, name="activity"),
    path("<int:pk>/settings/", views.project_detail_hub, {"tab": "settings"}, name="settings"),
    path("<int:pk>/archive/", views.project_archive_view, name="archive"),
    path("<int:pk>/delete/", views.project_delete_view, name="delete"),
]