from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .models import Notification
from accounts.models import User
from projects.models import Project, ProjectMember
from projects.views import check_project_access

@login_required
def notification_inbox_view(request):
    user = request.user
    filter_type = request.GET.get("type", "")
    
    qs = Notification.objects.filter(recipient=user).select_related("actor")
    
    if filter_type:
        qs = qs.filter(notification_type=filter_type)

    if request.method == "POST" and "mark_all_read" in request.POST:
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


@login_required
def notification_mark_read_view(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.is_read = True
    notif.save()
    if notif.link:
        return redirect(notif.link)
    return redirect("notifications:inbox")


@login_required
def notification_delete_view(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.delete()
    messages.success(request, "Notification dismissed.")
    return redirect("notifications:inbox")


@login_required
def accept_invitation_view(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user, notification_type="PROJECT_INVITATION")
    if notif.project:
        pm, created = ProjectMember.objects.get_or_create(
            project=notif.project,
            user=request.user,
            defaults={"role": notif.invitation_role or "DEVELOPER", "capacity_hours_per_week": 40}
        )
        if not created and notif.invitation_role:
            pm.role = notif.invitation_role
            pm.save()
            
        notif.invitation_status = "ACCEPTED"
        notif.is_read = True
        notif.save()
        messages.success(request, f"🎉 You have successfully joined '{notif.project.name}' as {notif.invitation_role.capitalize()}!")
        return redirect("projects:detail", pk=notif.project.id)
    else:
        messages.error(request, "The workspace project no longer exists.")
        return redirect("notifications:inbox")


@login_required
def decline_invitation_view(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user, notification_type="PROJECT_INVITATION")
    notif.invitation_status = "DECLINED"
    notif.save()
    messages.info(request, f"Invitation to '{notif.project.name if notif.project else 'workspace'}' declined.")
    return redirect("notifications:inbox")


class NotificationAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user = request.user
        if not user or not user.is_authenticated:
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
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)
        return Response({"success": True, "message": "All notifications marked as read."})
