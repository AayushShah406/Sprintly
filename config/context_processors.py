from django.db.models import Q
from projects.models import Project
from notifications.models import Notification

def global_workspace_context(request):
    try:
        user = request.user
        if user and user.is_authenticated:
            # Strictly user's accessible projects
            projects = list(
                Project.objects.filter(
                    Q(owner=user) | Q(memberships__user=user),
                    is_archived=False
                ).distinct().order_by("-created_at")
            )
            unread_count = Notification.objects.filter(recipient=user, is_read=False).count()
            active = projects[0] if projects else None
            return {
                "all_projects": projects,
                "project": active,
                "active_project": active,
                "current_user": user,
                "unread_notifications": unread_count,
            }
        else:
            return {
                "all_projects": [],
                "project": None,
                "active_project": None,
                "current_user": None,
                "unread_notifications": 0,
            }
    except Exception:
        return {
            "all_projects": [],
            "project": None,
            "active_project": None,
            "current_user": None,
            "unread_notifications": 0,
        }
