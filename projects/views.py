import json
from datetime import date, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.http import JsonResponse, HttpResponseForbidden
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Project, ProjectMember
from sprints.models import Sprint
from issues.models import Issue, SubTask, Comment, IssueAuditLog
from accounts.models import User
from analytics.health_service import SprintHealthEngine
from mongodb_engine.manager import mongo_manager

def get_current_user(request):
    if request.user.is_authenticated:
        return request.user
    return User.objects.first()

def check_project_access(project, user, required_roles=None):
    """Verifies that user is a member of the project. Auto-enrolls if in workspace."""
    if not user or not project:
        return True
    if user.is_superuser or project.owner == user:
        return True
    membership = project.memberships.filter(user=user).first()
    if not membership:
        ProjectMember.objects.create(project=project, user=user, role="DEVELOPER")
        return True
    if required_roles:
        return membership.role in required_roles
    return True

# 1. Projects Directory List
def project_list_view(request):
    user = get_current_user(request)
    search = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "")
    owner_filter = request.GET.get("owner", "")
    sort_by = request.GET.get("sort", "-created_at")

    qs = Project.objects.filter(is_archived=False).prefetch_related("memberships__user", "issues", "sprints")

    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(key__icontains=search) | Q(description__icontains=search))
    if status_filter:
        qs = qs.filter(status=status_filter)
    if owner_filter:
        qs = qs.filter(owner_id=owner_filter)

    qs = qs.order_by(sort_by)

    # Handle project creation via form POST
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        key = request.POST.get("key", "").strip().upper()
        description = request.POST.get("description", "").strip()
        category = request.POST.get("category", "Software Development")
        avatar_color = request.POST.get("avatar_color", "#4f46e5")

        if name and key:
            if Project.objects.filter(key=key).exists():
                messages.error(request, f"Project key '{key}' is already in use.")
            else:
                project = Project.objects.create(
                    name=name,
                    key=key,
                    description=description,
                    category=category,
                    avatar_color=avatar_color,
                    owner=user,
                    lead=user,
                )
                if user:
                    ProjectMember.objects.create(project=project, user=user, role="OWNER")
                mongo_manager.sync_project(project)
                messages.success(request, f"Project '{project.name}' created successfully!")
                return redirect("projects:detail", pk=project.pk)

    context = {
        "current_user": user,
        "projects": qs,
        "search": search,
        "status_filter": status_filter,
        "owner_filter": owner_filter,
        "sort_by": sort_by,
        "owners": User.objects.filter(is_active=True),
    }
    return render(request, "projects/project_list.html", context)


# 2. Project Hub & Sub-Tabs
def project_detail_hub(request, pk, tab="overview"):
    user = get_current_user(request)
    project = Project.objects.filter(pk=pk).first()
    
    # Graceful fallback if requested project ID is invalid or does not exist
    if not project:
        fallback = Project.objects.filter(is_archived=False).first()
        if fallback:
            return redirect(f"/projects/{fallback.pk}/{tab}/")
        else:
            messages.info(request, "No projects currently exist. Please create your first project.")
            return redirect("projects:list")

    check_project_access(project, user)

    today = date.today()
    all_issues = project.issues.select_related("assignee", "reporter", "sprint", "epic").all()
    sprints = project.sprints.all().order_by("-sprint_number")
    active_sprint = project.sprints.filter(status="ACTIVE").first()
    members = project.memberships.select_related("user").all()

    # Dynamic metrics strictly from DB
    total_issues = all_issues.count()
    done_issues = all_issues.filter(status="DONE").count()
    progress_pct = int((done_issues / total_issues) * 100) if total_issues > 0 else 0
    
    health_data = None
    if active_sprint:
        health_data = SprintHealthEngine.evaluate_sprint(active_sprint)

    # Handle Member Add or Role Update on Team tab
    if request.method == "POST" and "member_user_id" in request.POST:
        user_id = request.POST.get("member_user_id")
        new_role = request.POST.get("member_role", "DEVELOPER")
        target_user = User.objects.filter(pk=user_id).first()
        if target_user:
            pm, _ = ProjectMember.objects.get_or_create(project=project, user=target_user)
            pm.role = new_role
            pm.save()
            messages.success(request, f"Updated role for {target_user.display_name} to {pm.get_role_display()}.")
            return redirect("projects:team", pk=project.pk)

    # Handle Invite / Add New Teammate
    if request.method == "POST" and "new_teammate_email" in request.POST:
        email = request.POST.get("new_teammate_email", "").strip().lower()
        first_name = request.POST.get("new_teammate_first_name", "").strip()
        last_name = request.POST.get("new_teammate_last_name", "").strip()
        role = request.POST.get("new_teammate_role", "DEVELOPER")
        job_title = request.POST.get("new_teammate_title", "Software Engineer").strip()
        raw_cap = request.POST.get("new_teammate_capacity", 40)
        try:
            capacity = int(raw_cap)
        except (ValueError, TypeError):
            capacity = 40

        if not email:
            messages.error(request, "Teammate email address is required.")
        else:
            teammate = User.objects.filter(email__iexact=email).first()
            if not teammate:
                base_user = email.split("@")[0].replace(".", "_")
                username = base_user
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_user}_{counter}"
                    counter += 1

                import random
                colors = ["#4f46e5", "#0ea5e9", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4"]
                teammate = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name or base_user.capitalize(),
                    last_name=last_name,
                    role=role,
                    title=job_title,
                    avatar_color=random.choice(colors),
                    is_email_verified=True
                )
                teammate.set_password("SprintlyPass2026!")
                teammate.save()
                try:
                    from mongodb_engine.manager import mongo_manager
                    mongo_manager.sync_user(teammate)
                except Exception:
                    pass

            pm, _ = ProjectMember.objects.get_or_create(project=project, user=teammate)
            pm.role = role
            pm.capacity_hours_per_week = capacity
            pm.save()
            
            # Send appealing invitation email
            from accounts.email_service import send_invitation_email
            send_invitation_email(user, teammate, project, pm.get_role_display())

            messages.success(request, f"Teammate {teammate.display_name} ({teammate.email}) added to {project.name}!")
            return redirect("projects:team", pk=project.pk)

    # Handle Create Sprint
    if request.method == "POST" and "sprint_name" in request.POST:
        name = request.POST.get("sprint_name", "").strip()
        goal = request.POST.get("sprint_goal", "").strip()
        raw_dur = request.POST.get("duration_days", 14)
        try:
            duration_days = int(raw_dur)
        except (ValueError, TypeError):
            duration_days = 14

        start_date = date.today()
        raw_start = request.POST.get("start_date")
        if raw_start:
            from datetime import datetime
            for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"]:
                try:
                    start_date = datetime.strptime(str(raw_start).strip(), fmt).date()
                    break
                except ValueError:
                    pass
        end_date = start_date + timedelta(days=duration_days)

        next_num = (project.sprints.count() or 0) + 1
        sprint = Sprint.objects.create(
            project=project,
            name=name or f"Sprint {next_num}",
            sprint_number=next_num,
            goal=goal,
            status="PLANNING",
            start_date=start_date,
            end_date=end_date
        )
        try:
            from mongodb_engine.manager import mongo_manager
            mongo_manager.sync_sprint(sprint)
        except Exception:
            pass
        messages.success(request, f"Sprint '{sprint.name}' created successfully!")
        return redirect(f"/projects/{project.pk}/{tab}/")

    # Handle Create Epic
    if request.method == "POST" and "epic_title" in request.POST:
        title = request.POST.get("epic_title", "").strip()
        desc = request.POST.get("epic_description", "").strip()
        priority = request.POST.get("epic_priority", "HIGH")
        epic = Issue.objects.create(
            project=project,
            title=title,
            description=desc,
            issue_type="EPIC",
            priority=priority,
            status="TODO",
            story_points=13,
            reporter=user or project.owner,
        )
        try:
            from mongodb_engine.manager import mongo_manager
            mongo_manager.sync_issue(epic)
        except Exception:
            pass
        messages.success(request, f"Epic '{epic.key} - {epic.title}' created successfully!")
        return redirect(f"/projects/{project.pk}/roadmap/")

    # Handle Assign / Move Issue between Sprints and Backlog
    if request.method == "POST" and "assign_issue_id" in request.POST:
        issue_id = request.POST.get("assign_issue_id")
        target_sprint_id = request.POST.get("target_sprint_id")
        issue = Issue.objects.filter(pk=issue_id, project=project).first()
        if issue:
            if target_sprint_id == "backlog" or not target_sprint_id:
                issue.sprint = None
                if issue.status != "DONE":
                    issue.status = "BACKLOG"
            else:
                sprint_obj = Sprint.objects.filter(pk=target_sprint_id, project=project).first()
                issue.sprint = sprint_obj
                if sprint_obj and sprint_obj.status == "ACTIVE" and issue.status == "BACKLOG":
                    issue.status = "TODO"
            issue.save()
            try:
                from mongodb_engine.manager import mongo_manager
                mongo_manager.sync_issue(issue)
            except Exception:
                pass
            messages.success(request, f"Moved {issue.key} to {'Backlog' if not issue.sprint else issue.sprint.name}.")
            return redirect(f"/projects/{project.pk}/{tab}/")

    # Handle Remove Member from project
    if request.method == "POST" and "remove_member_id" in request.POST:
        member_id = request.POST.get("remove_member_id")
        pm = ProjectMember.objects.filter(project=project, pk=member_id).first()
        if pm:
            name = pm.user.display_name
            pm.delete()
            messages.success(request, f"Removed {name} from {project.name}.")
            return redirect("projects:team", pk=project.pk)

    # Tab specific context
    tab_context = {
        "current_user": user,
        "project": project,
        "active_tab": tab,
        "all_issues": all_issues,
        "sprints": sprints,
        "active_sprint": active_sprint,
        "members": members,
        "available_users": User.objects.filter(is_active=True).exclude(id__in=members.values_list("user_id", flat=True)),
        "total_issues": total_issues,
        "done_issues": done_issues,
        "open_issues": total_issues - done_issues,
        "progress_pct": progress_pct,
        "health_data": health_data,
        "all_projects": Project.objects.filter(is_archived=False),
    }

    # Tab: Board (Kanban)
    if tab == "board":
        tab_context["columns"] = {
            "BACKLOG": all_issues.filter(status="BACKLOG"),
            "TODO": all_issues.filter(status="TODO"),
            "IN_PROGRESS": all_issues.filter(status="IN_PROGRESS"),
            "IN_REVIEW": all_issues.filter(status="IN_REVIEW"),
            "BLOCKED": all_issues.filter(status="BLOCKED"),
            "DONE": all_issues.filter(status="DONE"),
        }

    # Tab: Backlog
    elif tab == "backlog":
        tab_context["backlog_issues"] = all_issues.filter(sprint__isnull=True)
        tab_context["active_sprint_issues"] = all_issues.filter(sprint=active_sprint) if active_sprint else []
        tab_context["future_sprints"] = sprints.filter(status="PLANNING")

    # Tab: Roadmap (Dynamic Real-Time Gantt Chart & Epics)
    elif tab == "roadmap":
        epics = list(all_issues.filter(issue_type="EPIC"))
        for epic in epics:
            children = all_issues.filter(epic=epic)
            c_total = children.count()
            c_done = children.filter(status="DONE").count()
            epic.calculated_progress = int((c_done / c_total) * 100) if c_total > 0 else (100 if epic.status == "DONE" else 0)
            epic.children_count = c_total
        tab_context["epics"] = epics

        # Build initial Gantt Chart data
        gantt_data = build_gantt_data(project)
        tab_context["gantt_data"] = gantt_data
        tab_context["gantt_data_json"] = json.dumps(gantt_data)

    # Tab: Reports (100% Dynamic from DB)
    elif tab == "reports":
        completed_sprints = list(sprints.filter(status="COMPLETED").order_by("sprint_number"))
        if active_sprint:
            completed_sprints.append(active_sprint)

        velocity_labels = [s.name for s in completed_sprints]
        velocity_committed = [s.total_committed_points for s in completed_sprints]
        velocity_completed = [s.completed_points for s in completed_sprints]

        priority_counts = [
            all_issues.filter(priority="CRITICAL").count(),
            all_issues.filter(priority="HIGH").count(),
            all_issues.filter(priority="MEDIUM").count(),
            all_issues.filter(priority="LOW").count(),
        ]

        tab_context["velocity_labels_json"] = json.dumps(velocity_labels)
        tab_context["velocity_committed_json"] = json.dumps(velocity_committed)
        tab_context["velocity_completed_json"] = json.dumps(velocity_completed)
        tab_context["priority_counts_json"] = json.dumps(priority_counts)

    # Tab: Activity
    elif tab == "activity":
        tab_context["activity_logs"] = IssueAuditLog.objects.filter(issue__project=project).select_related("issue", "actor").order_by("-created_at")[:50]

    return render(request, "projects/project_detail.html", tab_context)


def build_gantt_data(project):
    """Calculates chronological positions and progress for Epics and Sprints."""
    today = date.today()
    all_issues = project.issues.select_related("assignee", "epic").all()
    sprints = project.sprints.all().order_by("sprint_number")
    
    start_bound = today - timedelta(days=7)
    end_bound = today + timedelta(days=60)
    total_days = max(1, (end_bound - start_bound).days)

    gantt_items = []
    # 1. Epics
    for epic in all_issues.filter(issue_type="EPIC"):
        s_date = epic.created_at.date() if epic.created_at else today
        e_date = epic.due_date if epic.due_date else s_date + timedelta(days=30)
        offset_days = (s_date - start_bound).days
        dur_days = max(1, (e_date - s_date).days)
        left_pct = max(0.0, min(95.0, (offset_days / total_days) * 100))
        width_pct = max(5.0, min(100.0 - left_pct, (dur_days / total_days) * 100))

        children = all_issues.filter(epic=epic)
        c_tot = children.count()
        c_done = children.filter(status="DONE").count()
        prog = int((c_done / c_tot) * 100) if c_tot > 0 else (100 if epic.status == "DONE" else 0)

        gantt_items.append({
            "id": f"epic-{epic.id}",
            "type": "EPIC",
            "key": epic.key,
            "title": epic.title,
            "status": epic.status,
            "status_display": epic.get_status_display(),
            "start_date": s_date.strftime("%Y-%m-%d"),
            "end_date": e_date.strftime("%Y-%m-%d"),
            "duration_days": dur_days,
            "progress": prog,
            "left_pct": round(left_pct, 1),
            "width_pct": round(width_pct, 1),
            "color": "#7c3aed",
            "assignee": epic.assignee.display_name if epic.assignee else "Unassigned",
            "children_count": c_tot
        })

    # 2. Sprints
    for sprint in sprints:
        s_date = sprint.start_date if sprint.start_date else today
        e_date = sprint.end_date if sprint.end_date else s_date + timedelta(days=14)
        offset_days = (s_date - start_bound).days
        dur_days = max(1, (e_date - s_date).days)
        left_pct = max(0.0, min(95.0, (offset_days / total_days) * 100))
        width_pct = max(5.0, min(100.0 - left_pct, (dur_days / total_days) * 100))

        s_tot = sprint.total_committed_points or sum(i.story_points for i in sprint.issues.all())
        s_done = sprint.completed_points or sum(i.story_points for i in sprint.issues.filter(status="DONE"))
        prog = int((s_done / s_tot) * 100) if s_tot > 0 else 0

        gantt_items.append({
            "id": f"sprint-{sprint.id}",
            "type": "SPRINT",
            "key": f"SPRINT-{sprint.sprint_number}",
            "title": sprint.name,
            "status": sprint.status,
            "status_display": sprint.status,
            "start_date": s_date.strftime("%Y-%m-%d"),
            "end_date": e_date.strftime("%Y-%m-%d"),
            "duration_days": dur_days,
            "progress": prog,
            "left_pct": round(left_pct, 1),
            "width_pct": round(width_pct, 1),
            "color": "#4f46e5" if sprint.status == "ACTIVE" else "#0ea5e9",
            "assignee": f"{sprint.issues.count()} tasks",
            "children_count": sprint.issues.count()
        })

    # 3. Tasks / Stories if no epics
    if not gantt_items:
        for task in all_issues.filter(issue_type__in=["STORY", "TASK", "IMPROVEMENT"])[:8]:
            s_date = task.created_at.date() if task.created_at else today
            e_date = task.due_date if task.due_date else s_date + timedelta(days=7)
            offset_days = (s_date - start_bound).days
            dur_days = max(1, (e_date - s_date).days)
            left_pct = max(0.0, min(95.0, (offset_days / total_days) * 100))
            width_pct = max(5.0, min(100.0 - left_pct, (dur_days / total_days) * 100))
            prog = 100 if task.status == "DONE" else (50 if task.status == "IN_PROGRESS" else 0)

            gantt_items.append({
                "id": f"task-{task.id}",
                "type": task.issue_type,
                "key": task.key,
                "title": task.title,
                "status": task.status,
                "status_display": task.get_status_display(),
                "start_date": s_date.strftime("%Y-%m-%d"),
                "end_date": e_date.strftime("%Y-%m-%d"),
                "duration_days": dur_days,
                "progress": prog,
                "left_pct": round(left_pct, 1),
                "width_pct": round(width_pct, 1),
                "color": "#10b981" if task.status == "DONE" else "#f59e0b",
                "assignee": task.assignee.display_name if task.assignee else "Unassigned",
                "children_count": 0
            })

    timeline_weeks = []
    cur = start_bound
    while cur <= end_bound:
        timeline_weeks.append({
            "label": cur.strftime("%b %d"),
            "date": cur.strftime("%Y-%m-%d")
        })
        cur += timedelta(days=7)

    return {
        "project_name": project.name,
        "start_bound": start_bound.strftime("%Y-%m-%d"),
        "end_bound": end_bound.strftime("%Y-%m-%d"),
        "total_days": total_days,
        "timeline_weeks": timeline_weeks,
        "items": gantt_items
    }


class ProjectGanttDataAPI(APIView):
    """Real-Time Gantt Chart API endpoint for live asynchronous updates."""
    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        data = build_gantt_data(project)
        return Response(data, status=status.HTTP_200_OK)


def project_archive_view(request, pk):
    project = get_object_or_404(Project, pk=pk)
    project.is_archived = True
    project.status = "ARCHIVED"
    project.save()
    mongo_manager.sync_project(project)
    messages.success(request, f"Project '{project.name}' has been archived.")
    return redirect("projects:list")


def project_delete_view(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        name = project.name
        project.delete()
        messages.success(request, f"Project '{name}' was permanently deleted.")
        return redirect("projects:list")
    
    return redirect("projects:detail", pk=pk)