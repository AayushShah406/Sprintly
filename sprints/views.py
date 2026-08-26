from datetime import date, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .models import Sprint
from projects.models import Project
from issues.models import Issue
from analytics.health_service import SprintHealthEngine

def sprint_detail_page(request, pk):
    sprint = get_object_or_404(Sprint.objects.select_related("project"), pk=pk)
    issues = sprint.issues.select_related("assignee", "reporter").all()
    
    total_pts = sum(i.story_points for i in issues)
    done_pts = sum(i.story_points for i in issues if i.status == "DONE")
    remaining_pts = max(0, total_pts - done_pts)
    progress_pct = int((done_pts / total_pts) * 100) if total_pts > 0 else 0

    health_data = SprintHealthEngine.evaluate_sprint(sprint)

    # Team members in this sprint
    assignee_ids = issues.filter(assignee__isnull=False).values_list("assignee_id", flat=True).distinct()
    from accounts.models import User
    team_members = User.objects.filter(id__in=assignee_ids)

    context = {
        "sprint": sprint,
        "project": sprint.project,
        "issues": issues,
        "total_pts": total_pts,
        "done_pts": done_pts,
        "remaining_pts": remaining_pts,
        "progress_pct": progress_pct,
        "health_data": health_data,
        "team_members": team_members,
        "future_sprints": sprint.project.sprints.filter(status="PLANNING").exclude(pk=sprint.pk),
    }
    return render(request, "sprints/sprint_detail.html", context)


def sprint_start_action(request, pk):
    sprint = get_object_or_404(Sprint, pk=pk)
    if request.method == "POST":
        duration = int(request.POST.get("duration_days", 14))
        start_date = date.today()
        end_date = start_date + timedelta(days=duration)

        # Complete any other active sprints in the project
        Sprint.objects.filter(project=sprint.project, status="ACTIVE").update(status="COMPLETED")

        total_pts = sum(i.story_points for i in sprint.issues.all())
        sprint.status = "ACTIVE"
        sprint.start_date = start_date
        sprint.end_date = end_date
        sprint.total_committed_points = total_pts
        sprint.save()
        try:
            from mongodb_engine.manager import mongo_manager
            mongo_manager.sync_sprint(sprint)
        except Exception:
            pass

        SprintHealthEngine.evaluate_sprint(sprint)
        messages.success(request, f"Sprint '{sprint.name}' is now ACTIVE!")
    
    return redirect("sprints:detail", pk=sprint.pk)


def sprint_complete_action(request, pk):
    sprint = get_object_or_404(Sprint, pk=pk)
    if request.method == "POST":
        target_sprint_id = request.POST.get("target_sprint_id")
        incomplete_issues = sprint.issues.exclude(status="DONE")
        incomplete_count = incomplete_issues.count()

        if target_sprint_id and target_sprint_id != "backlog":
            target_sprint = Sprint.objects.filter(pk=target_sprint_id).first()
            if target_sprint:
                incomplete_issues.update(sprint=target_sprint)
        else:
            # Move to backlog
            incomplete_issues.update(sprint=None, status="BACKLOG")

        sprint.status = "COMPLETED"
        sprint.completed_points = sum(i.story_points for i in sprint.issues.filter(status="DONE"))
        sprint.save()
        try:
            from mongodb_engine.manager import mongo_manager
            mongo_manager.sync_sprint(sprint)
        except Exception:
            pass

        messages.success(request, f"Sprint '{sprint.name}' completed! {incomplete_count} incomplete tasks rolled over.")

    return redirect("projects:detail", pk=sprint.project.pk)
