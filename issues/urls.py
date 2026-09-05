from django.urls import path
from . import views

app_name = "issues"

urlpatterns = [
    # Full HTML Views
    path("create/", views.issue_create_view, name="create"),
    path("<int:pk>/", views.issue_detail_page, name="detail"),
    path("<int:pk>/edit/", views.issue_edit_view, name="edit"),
    path("<int:pk>/delete/", views.issue_delete_view, name="delete"),
    path("subtasks/<int:subtask_pk>/delete/", views.subtask_delete_view, name="subtask_delete"),
    path("links/<int:link_pk>/delete/", views.issue_link_delete_view, name="link_delete"),
    
    # REST API endpoints for /api/issues/ and /issues/
    path("", views.IssueListCreateAPI.as_view(), name="api_list_create"),
    path("api/", views.IssueListCreateAPI.as_view(), name="api_list_create_alt"),
    path("<int:pk>/move/", views.IssueMoveStatusAPI.as_view(), name="api_move_status"),
    path("api/<int:pk>/move/", views.IssueMoveStatusAPI.as_view(), name="api_move_status_alt"),
    path("subtasks/<int:subtask_pk>/toggle/", views.SubtaskToggleAPI.as_view(), name="api_subtask_toggle"),
    path("api/subtasks/<int:subtask_pk>/toggle/", views.SubtaskToggleAPI.as_view(), name="api_subtask_toggle_alt"),
    path("<int:pk>/watch/", views.WatcherToggleAPI.as_view(), name="api_watch_toggle"),
    path("api/<int:pk>/watch/", views.WatcherToggleAPI.as_view(), name="api_watch_toggle_alt"),
]
