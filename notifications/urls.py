from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_inbox_view, name="inbox"),
    path("<int:pk>/read/", views.notification_mark_read_view, name="mark_read"),
    path("<int:pk>/delete/", views.notification_delete_view, name="delete"),
    path("invitations/<int:pk>/accept/", views.accept_invitation_view, name="accept_invitation"),
    path("invitations/<int:pk>/decline/", views.decline_invitation_view, name="decline_invitation"),
    path("api/", views.NotificationAPI.as_view(), name="api"),
]
