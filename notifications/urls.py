from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_inbox_view, name="inbox"),
    path("<int:pk>/read/", views.notification_mark_read_view, name="mark_read"),
    path("<int:pk>/delete/", views.notification_delete_view, name="delete"),
    path("api/", views.NotificationAPI.as_view(), name="api"),
    
    # Team Chat App Routes
    path("chat/", views.team_chat_view, name="team_chat"),
    path("chat/<int:room_id>/", views.team_chat_view, name="room_chat"),
    path("chat/rooms/<int:room_id>/messages/", views.RoomMessagesAPI.as_view(), name="room_messages_api"),
    path("api/chat/rooms/<int:room_id>/messages/", views.RoomMessagesAPI.as_view(), name="room_messages_api_alt"),
]
