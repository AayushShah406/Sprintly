from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .models import Notification, TeamRoom, ChatMessage
from accounts.models import User
from projects.models import Project

def get_current_user(request):
    if request.user.is_authenticated:
        return request.user
    return User.objects.filter(is_active=True).first()

def notification_inbox_view(request):
    user = get_current_user(request)
    filter_type = request.GET.get("type", "")
    
    qs = Notification.objects.filter(recipient=user).select_related("actor") if user else Notification.objects.none()
    
    if filter_type:
        qs = qs.filter(notification_type=filter_type)

    if request.method == "POST" and "mark_all_read" in request.POST:
        if user:
            Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)
            messages.success(request, "All notifications marked as read.")
        return redirect("notifications:inbox")

    context = {
        "current_user": user,
        "notifications": qs[:50],
        "unread_count": qs.filter(is_read=False).count(),
        "filter_type": filter_type,
    }
    return render(request, "notifications/notification_list.html", context)


def notification_mark_read_view(request, pk):
    notif = get_object_or_404(Notification, pk=pk)
    notif.is_read = True
    notif.save()
    if notif.link:
        return redirect(notif.link)
    return redirect("notifications:inbox")


def notification_delete_view(request, pk):
    notif = get_object_or_404(Notification, pk=pk)
    notif.delete()
    messages.success(request, "Notification dismissed.")
    return redirect("notifications:inbox")


# =========================================================================
# REAL-TIME TEAM CHAT ROOMS & DIRECT MESSAGING
# =========================================================================
def team_chat_view(request, room_id=None):
    user = get_current_user(request)
    project = Project.objects.filter(is_archived=False).first()
    
    # Ensure default channels exist
    if project:
        TeamRoom.objects.get_or_create(project=project, name="general", defaults={"description": "General project discussion"})
        TeamRoom.objects.get_or_create(project=project, name="dev-team", defaults={"description": "Engineering and technical updates"})
        TeamRoom.objects.get_or_create(project=project, name="sprint-planning", defaults={"description": "Sprint objectives and task coordination"})

    all_rooms = TeamRoom.objects.select_related("project").all().order_by("name")
    active_room = None
    if room_id:
        active_room = TeamRoom.objects.filter(pk=room_id).first()
    if not active_room:
        active_room = all_rooms.first()

    teammates = User.objects.filter(is_active=True).exclude(pk=user.pk if user else None)

    # Initial messages for active room (last 50)
    messages_list = []
    if active_room:
        messages_list = list(active_room.messages.select_related("author").all().order_by("created_at"))[-50:]

    context = {
        "current_user": user,
        "project": project,
        "all_rooms": all_rooms,
        "active_room": active_room,
        "teammates": teammates,
        "chat_messages": messages_list,
    }
    return render(request, "notifications/team_chat.html", context)


class RoomMessagesAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request, room_id):
        room = get_object_or_404(TeamRoom, pk=room_id)
        # Avoid negative slicing on queryset by converting to list or using standard order
        messages_qs = room.messages.select_related("author").all().order_by("-created_at")[:50]
        messages = list(reversed(messages_qs))
        
        data = [{
            "id": m.id,
            "author_id": m.author.id,
            "author_name": m.author.display_name,
            "author_initials": m.author.initials,
            "author_role": m.author.get_role_display() if hasattr(m.author, "get_role_display") else "Member",
            "author_avatar_color": getattr(m.author, "avatar_color", "#4f46e5"),
            "content": m.content,
            "created_at": m.created_at.strftime("%I:%M %p"),
        } for m in messages]
        
        return Response({
            "room_id": room.id,
            "room_name": room.name,
            "messages": data
        })

    def post(self, request, room_id):
        user = get_current_user(request)
        if not user:
            return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        
        room = get_object_or_404(TeamRoom, pk=room_id)
        content = request.data.get("content", "").strip()
        if not content:
            return Response({"error": "Message content cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)

        msg = ChatMessage.objects.create(
            room=room,
            author=user,
            content=content
        )

        return Response({
            "success": True,
            "message": {
                "id": msg.id,
                "author_id": user.id,
                "author_name": user.display_name,
                "author_initials": user.initials,
                "author_role": user.get_role_display() if hasattr(user, "get_role_display") else "Member",
                "author_avatar_color": getattr(user, "avatar_color", "#4f46e5"),
                "content": msg.content,
                "created_at": msg.created_at.strftime("%I:%M %p"),
            }
        }, status=status.HTTP_201_CREATED)


# REST API for top navbar bell counter and drawer
class NotificationAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user = get_current_user(request)
        if not user:
            return Response({"unread_count": 0, "notifications": []})

        notifications = Notification.objects.filter(recipient=user).order_by("-created_at")[:15]
        unread_count = Notification.objects.filter(recipient=user, is_read=False).count()

        data = [{
            "id": n.pk,
            "type": n.notification_type,
            "title": n.title,
            "message": n.message,
            "link": n.link,
            "is_read": n.is_read,
            "created_at": n.created_at.strftime("%b %d, %H:%M"),
        } for n in notifications]

        return Response({
            "unread_count": unread_count,
            "notifications": data
        })

    def post(self, request):
        user = get_current_user(request)
        if user:
            Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)
        return Response({"message": "Marked all as read."})
