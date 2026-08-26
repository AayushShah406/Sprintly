from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.http import JsonResponse
from projects.models import Project, ProjectMember
from sprints.models import Sprint
from issues.models import Issue, IssueAuditLog
from notifications.models import Notification
from accounts.models import User
from analytics.health_service import SprintHealthEngine

def get_current_user(request):
    """Helper to return logged in user or default demo admin."""
    if request.user.is_authenticated:
        return request.user
    return User.objects.first()

def landing_page_view(request):
    user = request.user if request.user.is_authenticated else None
    projects_count = Project.objects.filter(is_archived=False).count()
    issues_count = Issue.objects.count()
    sprints_count = Sprint.objects.count()
    
    context = {
        "current_user": user,
        "is_authenticated": request.user.is_authenticated,
        "metrics": {
            "projects_count": projects_count,
            "issues_count": issues_count,
            "sprints_count": sprints_count,
            "teams_count": User.objects.filter(is_active=True).count(),
        }
    }
    return render(request, "landing.html", context)

def dashboard_home(request):
    user = get_current_user(request)
    today = date.today()
    
    # User's accessible projects
    if user:
        member_project_ids = ProjectMember.objects.filter(user=user).values_list("project_id", flat=True)
        projects = Project.objects.filter(Q(id__in=member_project_ids) | Q(owner=user), is_archived=False).distinct().order_by("-created_at")
    else:
        projects = Project.objects.filter(is_archived=False).order_by("-created_at")

    active_project = projects.first()
    
    # Active sprint across workspace or in active project
    active_sprint = None
    if active_project:
        active_sprint = active_project.sprints.filter(status="ACTIVE").first()
    if not active_sprint:
        active_sprint = Sprint.objects.filter(status="ACTIVE").first()

    # User's issues
    my_assigned_issues = Issue.objects.filter(assignee=user).exclude(status="DONE").order_by("due_date", "-priority") if user else Issue.objects.none()
    my_created_issues = Issue.objects.filter(reporter=user).order_by("-created_at")[:5] if user else Issue.objects.none()
    
    # Due soon & overdue
    due_soon_issues = Issue.objects.filter(
        due_date__gte=today,
        due_date__lte=today + timedelta(days=5),
    ).exclude(status="DONE").order_by("due_date")
    
    overdue_issues = Issue.objects.filter(
        due_date__lt=today,
    ).exclude(status="DONE").order_by("due_date")

    # Completed this week
    completed_recent = Issue.objects.filter(status="DONE").order_by("-updated_at")[:6]

    # Metrics summary
    total_assigned = my_assigned_issues.count()
    total_due_soon = due_soon_issues.count()
    total_overdue = overdue_issues.count()
    total_completed = Issue.objects.filter(status="DONE").count()

    # Active sprint progress calculation
    sprint_health = None
    sprint_progress = 0
    if active_sprint:
        sprint_health = SprintHealthEngine.evaluate_sprint(active_sprint)
        total_pts = sprint_health.get("total_points", 0)
        done_pts = sprint_health.get("completed_points", 0)
        if total_pts > 0:
            sprint_progress = int((done_pts / total_pts) * 100)

    # Team workload summary: strictly active workspace members
    if active_project:
        member_user_ids = active_project.memberships.values_list("user_id", flat=True)
        team_members = User.objects.filter(id__in=member_user_ids, is_active=True).annotate(
            active_tickets=Count("assigned_issues", filter=~Q(assigned_issues__status="DONE"))
        ).order_by("-active_tickets")
    elif user:
        team_members = User.objects.filter(id=user.id).annotate(
            active_tickets=Count("assigned_issues", filter=~Q(assigned_issues__status="DONE"))
        )
    else:
        team_members = User.objects.none()

    # Recent business activity logs
    recent_activity = IssueAuditLog.objects.select_related("issue", "actor").order_by("-created_at")[:10]

    # Notifications count
    unread_notifications = Notification.objects.filter(recipient=user, is_read=False).count() if user else 0

    context = {
        "current_user": user,
        "projects": projects,
        "active_project": active_project,
        "active_sprint": active_sprint,
        "sprint_health": sprint_health,
        "sprint_progress": sprint_progress,
        "my_assigned_issues": my_assigned_issues[:6],
        "my_created_issues": my_created_issues,
        "due_soon_issues": due_soon_issues[:5],
        "overdue_issues": overdue_issues[:5],
        "completed_recent": completed_recent,
        "total_assigned": total_assigned,
        "total_due_soon": total_due_soon,
        "total_overdue": total_overdue,
        "total_completed": total_completed,
        "team_members": team_members,
        "recent_activity": recent_activity,
        "unread_notifications": unread_notifications,
    }
    return render(request, "dashboard/dashboard.html", context)


def my_work_view(request):
    user = get_current_user(request)
    today = date.today()
    
    assigned_all = Issue.objects.filter(assignee=user).select_related("project", "sprint") if user else Issue.objects.none()
    
    due_today = assigned_all.filter(due_date=today).exclude(status="DONE")
    due_this_week = assigned_all.filter(
        due_date__gte=today,
        due_date__lte=today + timedelta(days=7)
    ).exclude(status="DONE").order_by("due_date")
    
    overdue = assigned_all.filter(due_date__lt=today).exclude(status="DONE").order_by("due_date")
    in_progress = assigned_all.filter(status="IN_PROGRESS")
    in_review = assigned_all.filter(status="IN_REVIEW")
    completed = assigned_all.filter(status="DONE").order_by("-updated_at")[:10]

    # Filter by project if selected
    project_id = request.GET.get("project")
    if project_id:
        assigned_all = assigned_all.filter(project_id=project_id)

    context = {
        "current_user": user,
        "assigned_all": assigned_all,
        "due_today": due_today,
        "due_this_week": due_this_week,
        "overdue": overdue,
        "in_progress": in_progress,
        "in_review": in_review,
        "completed": completed,
        "projects": Project.objects.filter(is_archived=False),
        "selected_project_id": int(project_id) if project_id else None,
    }
    return render(request, "dashboard/my_work.html", context)


def activity_log_view(request):
    user = get_current_user(request)
    logs = IssueAuditLog.objects.select_related("issue", "actor").order_by("-created_at")[:50]
    
    project_id = request.GET.get("project")
    if project_id:
        logs = logs.filter(issue__project_id=project_id)

    context = {
        "current_user": user,
        "logs": logs,
        "projects": Project.objects.filter(is_archived=False),
        "selected_project_id": int(project_id) if project_id else None,
    }
    return render(request, "dashboard/activity.html", context)


def global_search_view(request):
    query = request.GET.get("q", "").strip()
    user = get_current_user(request)
    
    results = {
        "query": query,
        "projects": [],
        "issues": [],
        "epics": [],
        "sprints": [],
        "users": [],
    }

    if query:
        results["projects"] = list(Project.objects.filter(
            Q(name__icontains=query) | Q(key__icontains=query) | Q(description__icontains=query),
            is_archived=False
        ).values("id", "name", "key", "category")[:5])

        results["issues"] = list(Issue.objects.filter(
            Q(title__icontains=query) | Q(key__icontains=query) | Q(description__icontains=query)
        ).exclude(issue_type="EPIC").values("id", "key", "title", "status", "priority", "issue_type")[:10])

        results["epics"] = list(Issue.objects.filter(
            Q(title__icontains=query) | Q(key__icontains=query),
            issue_type="EPIC"
        ).values("id", "key", "title", "status")[:5])

        results["sprints"] = list(Sprint.objects.filter(
            Q(name__icontains=query) | Q(goal__icontains=query)
        ).values("id", "name", "status", "sprint_number")[:5])

        results["users"] = list(User.objects.filter(
            Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query),
            is_active=True
        ).values("id", "username", "first_name", "last_name", "role", "title")[:5])

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.GET.get("format") == "json":
        return JsonResponse(results)

    context = {
        "current_user": user,
        "results": results,
        "query": query,
    }
    return render(request, "dashboard/search.html", context)
