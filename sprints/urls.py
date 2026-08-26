from django.urls import path
from . import views

app_name = "sprints"

urlpatterns = [
    path("<int:pk>/", views.sprint_detail_page, name="detail"),
    path("<int:pk>/start/", views.sprint_start_action, name="start"),
    path("<int:pk>/complete/", views.sprint_complete_action, name="complete"),
]
