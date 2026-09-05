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

@login_required
def dashboard_home(request):
    user = request.user
    today = date.today()
    
    # Strictly user's accessible projects
    projects = Project.objects.filter(
        Q(owner=user) | Q(memberships__user=user),
        is_archived=False
    ).distinct().order_by("-created_at")

    user_project_ids = list(projects.values_list("id", flat=True))
    active_project = projects.first()
    
    # Active sprint strictly within user's active project
    active_sprint = None
    if active_project:
        active_sprint = active_project.sprints.filter(status="ACTIVE").first()

    # User's issues
    if user_project_ids:
        my_assigned_issues = Issue.objects.filter(
            assignee=user,
            project_id__in=user_project_ids
        ).exclude(status="DONE").order_by("due_date", "-priority")
        
        my_created_issues = Issue.objects.filter(
            reporter=user,
            project_id__in=user_project_ids
        ).order_by("-created_at")[:5]
        
        # Due soon & overdue
        due_soon_issues = Issue.objects.filter(
            project_id__in=user_project_ids,
            due_date__gte=today,
            due_date__lte=today + timedelta(days=5),
        ).exclude(status="DONE").order_by("due_date")
        
        overdue_issues = Issue.objects.filter(
            project_id__in=user_project_ids,
            due_date__lt=today,
        ).exclude(status="DONE").order_by("due_date")

        # Completed this week
        completed_recent = Issue.objects.filter(
            project_id__in=user_project_ids,
            status="DONE"
        ).order_by("-updated_at")[:6]

        total_completed = Issue.objects.filter(
            project_id__in=user_project_ids,
            status="DONE"
        ).count()

        # Recent business activity logs strictly within user's projects
        recent_activity = IssueAuditLog.objects.filter(
            issue__project_id__in=user_project_ids
        ).select_related("issue", "actor").order_by("-created_at")[:10]
    else:
        my_assigned_issues = Issue.objects.none()
        my_created_issues = Issue.objects.none()
        due_soon_issues = Issue.objects.none()
        overdue_issues = Issue.objects.none()
        completed_recent = Issue.objects.none()
        total_completed = 0
        recent_activity = IssueAuditLog.objects.none()

    # Metrics summary
    total_assigned = my_assigned_issues.count()
    total_due_soon = due_soon_issues.count()
    total_overdue = overdue_issues.count()

    # Active sprint progress calculation
    sprint_health = None
    sprint_progress = 0
    if active_sprint:
        sprint_health = SprintHealthEngine.evaluate_sprint(active_sprint)
        total_pts = sprint_health.get("total_points", 0)
        done_pts = sprint_health.get("completed_points", 0)
        if total_pts > 0:
            sprint_progress = int((done_pts / total_pts) * 100)

    # Team workload summary: strictly members of active project
    if active_project:
        member_user_ids = set(active_project.memberships.values_list("user_id", flat=True))
        # Include owner if not in memberships
        if active_project.owner_id:
            member_user_ids.add(active_project.owner_id)
        team_members = User.objects.filter(id__in=member_user_ids, is_active=True).distinct().annotate(
            active_tickets=Count("assigned_issues", filter=Q(assigned_issues__project=active_project) & ~Q(assigned_issues__status="DONE"))
        ).order_by("-active_tickets")
    else:
        team_members = User.objects.filter(id=user.id).distinct().annotate(
            active_tickets=Count("assigned_issues", filter=~Q(assigned_issues__status="DONE"))
        )

    # Notifications count
    unread_notifications = Notification.objects.filter(recipient=user, is_read=False).count()

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


@login_required
def my_work_view(request):
    user = request.user
    today = date.today()
    
    user_projects = Project.objects.filter(
        Q(owner=user) | Q(memberships__user=user),
        is_archived=False
    ).distinct().order_by("-created_at")
    user_project_ids = list(user_projects.values_list("id", flat=True))

    assigned_all = Issue.objects.filter(
        assignee=user,
        project_id__in=user_project_ids
    ).select_related("project", "sprint") if user_project_ids else Issue.objects.none()
    
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
    if project_id and project_id.isdigit():
        pid = int(project_id)
        if pid in user_project_ids:
            assigned_all = assigned_all.filter(project_id=pid)
        else:
            assigned_all = Issue.objects.none()

    context = {
        "current_user": user,
        "assigned_all": assigned_all,
        "due_today": due_today,
        "due_this_week": due_this_week,
        "overdue": overdue,
        "in_progress": in_progress,
        "in_review": in_review,
        "completed": completed,
        "projects": user_projects,
        "selected_project_id": int(project_id) if (project_id and project_id.isdigit()) else None,
    }
    return render(request, "dashboard/my_work.html", context)


@login_required
def activity_log_view(request):
    user = request.user
    user_projects = Project.objects.filter(
        Q(owner=user) | Q(memberships__user=user),
        is_archived=False
    ).distinct().order_by("-created_at")
    user_project_ids = list(user_projects.values_list("id", flat=True))

    logs = IssueAuditLog.objects.filter(
        issue__project_id__in=user_project_ids
    ).select_related("issue", "actor").order_by("-created_at")[:50] if user_project_ids else IssueAuditLog.objects.none()
    
    project_id = request.GET.get("project")
    if project_id and project_id.isdigit():
        pid = int(project_id)
        if pid in user_project_ids:
            logs = logs.filter(issue__project_id=pid)
        else:
            logs = IssueAuditLog.objects.none()

    context = {
        "current_user": user,
        "logs": logs,
        "projects": user_projects,
        "selected_project_id": int(project_id) if (project_id and project_id.isdigit()) else None,
    }
    return render(request, "dashboard/activity.html", context)


@login_required
def global_search_view(request):
    query = request.GET.get("q", "").strip()
    user = request.user
    
    user_projects = Project.objects.filter(
        Q(owner=user) | Q(memberships__user=user),
        is_archived=False
    ).distinct()
    user_project_ids = list(user_projects.values_list("id", flat=True))

    results = {
        "query": query,
        "projects": [],
        "issues": [],
        "epics": [],
        "sprints": [],
        "users": [],
    }

    if query and user_project_ids:
        results["projects"] = list(user_projects.filter(
            Q(name__icontains=query) | Q(key__icontains=query) | Q(description__icontains=query)
        ).values("id", "name", "key", "category")[:5])

        results["issues"] = list(Issue.objects.filter(
            project_id__in=user_project_ids
        ).filter(
            Q(title__icontains=query) | Q(key__icontains=query) | Q(description__icontains=query)
        ).exclude(issue_type="EPIC").values("id", "key", "title", "status", "priority", "issue_type")[:10])

        results["epics"] = list(Issue.objects.filter(
            project_id__in=user_project_ids,
            issue_type="EPIC"
        ).filter(
            Q(title__icontains=query) | Q(key__icontains=query)
        ).values("id", "key", "title", "status")[:5])

        results["sprints"] = list(Sprint.objects.filter(
            project_id__in=user_project_ids
        ).filter(
            Q(name__icontains=query) | Q(goal__icontains=query)
        ).values("id", "name", "status", "sprint_number")[:5])

        # Only find users that are teammates in user's projects
        teammate_ids = ProjectMember.objects.filter(project_id__in=user_project_ids).values_list("user_id", flat=True)
        results["users"] = list(User.objects.filter(
            id__in=teammate_ids,
            is_active=True
        ).filter(
            Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query)
        ).values("id", "username", "first_name", "last_name", "role", "title")[:5])

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.GET.get("format") == "json":
        return JsonResponse(results)

    context = {
        "current_user": user,
        "results": results,
        "query": query,
    }
    return render(request, "dashboard/search.html", context)


@login_required
def global_workspace_tab_view(request, tab="board"):
    user = request.user
    accessible_projects = Project.objects.filter(
        Q(owner=user) | Q(memberships__user=user),
        is_archived=False
    ).distinct().order_by("-created_at")

    if accessible_projects.exists():
        first_project = accessible_projects.first()
        return redirect(f"/projects/{first_project.id}/{tab}/")

    # If user has 0 projects, render the dedicated feature empty workspace page
    tab_configs = {
        "board": {
            "title": "Interactive Kanban Board",
            "icon": "kanban",
            "desc": "Drag-and-drop workflow tracking with custom columns (Backlog, Todo, In Progress, In Review, Blocked, Done).",
            "action_text": "Create Project to Launch Board"
        },
        "backlog": {
            "title": "Backlog & Story Estimation",
            "icon": "layers",
            "desc": "Prioritize user stories, estimate Fibonacci story points, and assign tickets into sprint iterations.",
            "action_text": "Create Project to Build Backlog"
        },
        "sprints": {
            "title": "Sprint Management & Iterations",
            "icon": "zap",
            "desc": "Run agile sprints with automated capacity burndown, velocity analysis, and sprint health scores.",
            "action_text": "Create Project to Start Sprints"
        },
        "roadmap": {
            "title": "Quarterly Agile Roadmap",
            "icon": "map",
            "desc": "Interactive Gantt timeline for cross-functional epics, milestone tracking, and dependency mapping.",
            "action_text": "Create Project for Roadmap"
        },
        "reports": {
            "title": "Agile Velocity & Health Reports",
            "icon": "bar-chart-2",
            "desc": "Cumulative flow diagrams, burndown metrics, story point velocity, and team throughput analytics.",
            "action_text": "Create Project for Reports"
        },
        "team": {
            "title": "Team Capacity & Workload",
            "icon": "users",
            "desc": "Manage developer workload, weekly hourly capacity, roles (Owner, Lead, Developer, QA), and invitations.",
            "action_text": "Create Project to Assemble Team"
        },
    }

    config = tab_configs.get(tab, {
        "title": f"{tab.capitalize()} Workspace",
        "icon": "layers",
        "desc": "Collaborative agile workspace tools for engineering teams.",
        "action_text": "Create Project"
    })

    context = {
        "current_user": user,
        "active_tab": tab,
        "tab_config": config,
        "all_projects": accessible_projects,
    }
    return render(request, "projects/empty_workspace_page.html", context)

