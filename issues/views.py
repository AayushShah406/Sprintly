from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Issue, SubTask, Comment, IssueAttachment, IssueLink, IssueAuditLog
from projects.models import Project
from projects.views import check_project_access
from sprints.models import Sprint
from accounts.models import User
from analytics.health_service import SprintHealthEngine

class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # Allow drag-and-drop actions without CSRF failure


# 1. Full-Page Issue Detail View
@login_required
def issue_detail_page(request, pk):
    issue = get_object_or_404(
        Issue.objects.select_related("project", "sprint", "epic", "assignee", "reporter")
        .prefetch_related("subtasks", "comments__author", "attachments", "outgoing_links__target_issue", "incoming_links__source_issue", "watchers"),
        pk=pk
    )
    user = request.user
    if not check_project_access(issue.project, user):
        messages.error(request, "Permission denied.")
        return redirect("projects:list")
    
    # Handle Comment submission via POST
    if request.method == "POST" and "comment_content" in request.POST:
        content = request.POST.get("comment_content", "").strip()
        if content:
            Comment.objects.create(issue=issue, author=user, content=content)
            IssueAuditLog.objects.create(issue=issue, actor=user, action="Added comment")
            messages.success(request, "Comment posted.")
            return redirect("issues:detail", pk=issue.pk)

    # Handle Subtask creation via POST
    if request.method == "POST" and "subtask_title" in request.POST:
        title = request.POST.get("subtask_title", "").strip()
        if title:
            SubTask.objects.create(issue=issue, title=title)
            IssueAuditLog.objects.create(issue=issue, actor=user, action=f"Added subtask '{title}'")
            messages.success(request, "Subtask added.")
            return redirect("issues:detail", pk=issue.pk)

    # Handle Attachment upload via POST
    if request.method == "POST" and "attachment_name" in request.POST:
        name = request.POST.get("attachment_name", "").strip()
        size = request.POST.get("attachment_size", "250 KB")
        if name:
            IssueAttachment.objects.create(issue=issue, file_name=name, file_size=size, uploaded_by=user)
            IssueAuditLog.objects.create(issue=issue, actor=user, action=f"Attached file '{name}'")
            messages.success(request, "Attachment recorded.")
            return redirect("issues:detail", pk=issue.pk)

    # Handle Link Issue via POST
    if request.method == "POST" and "target_issue_id" in request.POST:
        target_id = request.POST.get("target_issue_id")
        link_type = request.POST.get("link_type", "RELATES_TO")
        target_issue = Issue.objects.filter(pk=target_id, project=issue.project).first()
        if target_issue and target_issue != issue:
            IssueLink.objects.get_or_create(source_issue=issue, target_issue=target_issue, link_type=link_type)
            messages.success(request, f"Linked to {target_issue.key}.")
            return redirect("issues:detail", pk=issue.pk)

    member_user_ids = issue.project.memberships.values_list("user_id", flat=True)
    context = {
        "current_user": user,
        "issue": issue,
        "is_watching": issue.watchers.filter(pk=user.pk).exists() if user else False,
        "project": issue.project,
        "all_project_issues": issue.project.issues.exclude(pk=issue.pk),
        "users": User.objects.filter(id__in=member_user_ids, is_active=True),
        "sprints": issue.project.sprints.all(),
        "audit_logs": issue.audit_logs.select_related("actor").order_by("-created_at")[:20],
    }
    return render(request, "issues/issue_detail.html", context)


# 2. Issue Create View
@login_required
def issue_create_view(request):
    user = request.user
    user_projects = Project.objects.filter(
        Q(owner=user) | Q(memberships__user=user),
        is_archived=False
    ).distinct()

    if not user_projects.exists():
        messages.info(request, "Please create a project first before creating issues.")
        return redirect("projects:list")

    project_id = request.GET.get("project") or request.POST.get("project_id")
    project = user_projects.filter(pk=project_id).first() if project_id else user_projects.first()

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        desc = request.POST.get("description", "").strip()
        issue_type = request.POST.get("issue_type", "TASK")
        priority = request.POST.get("priority", "MEDIUM")
        status_val = request.POST.get("status", "TODO")
        try:
            points = int(request.POST.get("story_points", 3))
        except (ValueError, TypeError):
            points = 3

        assignee_id = request.POST.get("assignee_id")
        sprint_id = request.POST.get("sprint_id")
        epic_id = request.POST.get("epic_id")
        due_date = request.POST.get("due_date") or None
        labels = request.POST.get("labels", "").strip()

        if title and project:
            assignee = User.objects.filter(pk=assignee_id).first() if assignee_id else None
            sprint = project.sprints.filter(pk=sprint_id).first() if sprint_id else None
            epic = project.issues.filter(pk=epic_id, issue_type="EPIC").first() if epic_id else None

            issue = Issue.objects.create(
                project=project,
                title=title,
                description=desc,
                issue_type=issue_type,
                priority=priority,
                status=status_val,
                story_points=points,
                assignee=assignee,
                reporter=user,
                sprint=sprint,
                epic=epic,
                due_date=due_date,
                labels=labels,
            )

            IssueAuditLog.objects.create(issue=issue, actor=user, action="Created issue")
            try:
                from mongodb_engine.manager import mongo_manager
                mongo_manager.sync_issue(issue)
            except Exception:
                pass
            messages.success(request, f"Issue {issue.key} created successfully!")
            return redirect("issues:detail", pk=issue.pk)

    member_user_ids = project.memberships.values_list("user_id", flat=True) if project else []
    context = {
        "current_user": user,
        "project": project,
        "projects": user_projects,
        "sprints": project.sprints.all() if project else [],
        "epics": project.issues.filter(issue_type="EPIC") if project else [],
        "users": User.objects.filter(id__in=member_user_ids, is_active=True),
    }
    return render(request, "issues/issue_form.html", context)


# 3. Issue Edit & Quick Update
@login_required
def issue_edit_view(request, pk):
    issue = get_object_or_404(Issue, pk=pk)
    user = request.user
    if not check_project_access(issue.project, user):
        messages.error(request, "Permission denied.")
        return redirect("projects:list")

    if request.method == "POST":
        old_status = issue.status

        issue.title = request.POST.get("title", issue.title).strip()
        issue.description = request.POST.get("description", issue.description).strip()
        issue.issue_type = request.POST.get("issue_type", issue.issue_type)
        issue.priority = request.POST.get("priority", issue.priority)
        issue.status = request.POST.get("status", issue.status)
        try:
            issue.story_points = int(request.POST.get("story_points", issue.story_points))
        except (ValueError, TypeError):
            pass
        
        assignee_id = request.POST.get("assignee_id")
        issue.assignee = User.objects.filter(pk=assignee_id).first() if assignee_id else None
        
        sprint_id = request.POST.get("sprint_id")
        issue.sprint = issue.project.sprints.filter(pk=sprint_id).first() if sprint_id else None

        due_date = request.POST.get("due_date")
        issue.due_date = due_date if due_date else None
        issue.labels = request.POST.get("labels", issue.labels)

        issue.save()

        # Audit
        if old_status != issue.status:
            IssueAuditLog.objects.create(
                issue=issue, actor=user, action="Status changed",
                previous_value=old_status, new_value=issue.status
            )
        else:
            IssueAuditLog.objects.create(issue=issue, actor=user, action="Updated ticket details")

        # Recalculate sprint points if status changed
        if old_status != issue.status and issue.sprint:
            done_pts = sum(i.story_points for i in issue.sprint.issues.filter(status="DONE"))
            issue.sprint.completed_points = done_pts
            issue.sprint.save(update_fields=["completed_points"])
            SprintHealthEngine.evaluate_sprint(issue.sprint)

        if request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", ""):
            return JsonResponse({
                "status": "success",
                "message": f"Issue {issue.key} updated.",
                "issue": {
                    "id": issue.pk,
                    "key": issue.key,
                    "title": issue.title,
                    "status": issue.status,
                    "status_display": issue.get_status_display(),
                    "priority": issue.priority,
                    "story_points": issue.story_points,
                    "assignee": issue.assignee.display_name if issue.assignee else "Unassigned",
                    "sprint": issue.sprint.name if issue.sprint else "Backlog",
                }
            })

        messages.success(request, f"Issue {issue.key} updated.")
        return redirect("issues:detail", pk=issue.pk)

    return redirect("issues:detail", pk=issue.pk)


# 4. Issue Delete View
@login_required
def issue_delete_view(request, pk):
    issue = get_object_or_404(Issue, pk=pk)
    user = request.user
    is_authorized = (
        user.is_superuser or
        issue.project.owner == user or
        issue.reporter == user or
        check_project_access(issue.project, user, required_roles=["OWNER", "ADMIN", "MANAGER", "DEVELOPER", "TESTER"])
    )
    if not is_authorized:
        if request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", ""):
            return JsonResponse({"status": "error", "message": "Permission denied."}, status=403)
        messages.error(request, "Permission denied.")
        return redirect("issues:detail", pk=issue.pk)

    project_id = issue.project.pk
    key = issue.key
    sprint = issue.sprint
    issue.delete()

    # Recalculate sprint points if applicable
    if sprint:
        sprint.completed_points = sum(
            i.story_points for i in sprint.issues.filter(status="DONE")
        )
        sprint.save(update_fields=["completed_points"])
        SprintHealthEngine.evaluate_sprint(sprint)

    redirect_url = f"/projects/{project_id}/board/"

    if request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", ""):
        return JsonResponse({
            "status": "success",
            "message": f"Issue {key} was deleted.",
            "redirect_url": redirect_url
        })

    messages.success(request, f"Issue {key} was deleted.")
    return redirect(redirect_url)


# 4b. Subtask Delete View
@login_required
def subtask_delete_view(request, subtask_pk):
    subtask = get_object_or_404(SubTask, pk=subtask_pk)
    issue = subtask.issue
    user = request.user
    if not check_project_access(issue.project, user):
        return JsonResponse({"status": "error", "message": "Permission denied."}, status=403)

    subtask_title = subtask.title
    subtask.delete()
    IssueAuditLog.objects.create(issue=issue, actor=user, action=f"Removed subtask '{subtask_title}'")

    if request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", ""):
        return JsonResponse({
            "status": "success",
            "subtasks_completed": issue.subtasks_completed,
            "subtasks_total": issue.subtasks_total,
            "subtasks_progress": issue.subtasks_progress,
        })
    messages.success(request, "Subtask removed.")
    return redirect("issues:detail", pk=issue.pk)


# 4c. Issue Link Delete View
@login_required
def issue_link_delete_view(request, link_pk):
    link = get_object_or_404(IssueLink, pk=link_pk)
    issue = link.source_issue
    if not check_project_access(issue.project, request.user):
        return JsonResponse({"status": "error", "message": "Permission denied."}, status=403)
    link.delete()
    messages.success(request, "Issue link removed.")
    return redirect("issues:detail", pk=issue.pk)


# 5. REST API Endpoints for Drag-and-Drop Kanban and SPA Modals
class IssueListCreateAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user = request.user
        project_id = request.query_params.get("project_id")
        sprint_id = request.query_params.get("sprint_id")
        status_filter = request.query_params.get("status")
        assignee_id = request.query_params.get("assignee")
        search = request.query_params.get("search", "").strip()

        qs = Issue.objects.select_related("project", "sprint", "assignee", "reporter").all()

        if user and user.is_authenticated:
            user_project_ids = Project.objects.filter(
                Q(owner=user) | Q(memberships__user=user),
                is_archived=False
            ).values_list("id", flat=True)
            qs = qs.filter(project_id__in=user_project_ids)

        if project_id:
            qs = qs.filter(project_id=project_id)
        if sprint_id:
            if sprint_id == "backlog":
                qs = qs.filter(sprint__isnull=True)
            else:
                qs = qs.filter(sprint_id=sprint_id)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if assignee_id:
            qs = qs.filter(assignee_id=assignee_id)
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(key__icontains=search) | Q(description__icontains=search))

        data = [{
            "id": i.pk,
            "key": i.key,
            "title": i.title,
            "description": i.description,
            "issue_type": i.issue_type,
            "priority": i.priority,
            "status": i.status,
            "story_points": i.story_points,
            "labels": i.label_list,
            "due_date": str(i.due_date) if i.due_date else None,
            "is_overdue": i.is_overdue,
            "subtasks_total": i.subtasks_total,
            "subtasks_completed": i.subtasks_completed,
            "assignee": {
                "id": i.assignee.pk,
                "username": i.assignee.username,
                "name": i.assignee.display_name,
                "initials": i.assignee.initials,
                "avatar_color": i.assignee.avatar_color,
            } if i.assignee else None,
            "project": {"id": i.project.pk, "key": i.project.key, "name": i.project.name},
            "sprint": {"id": i.sprint.pk, "name": i.sprint.name} if i.sprint else None,
        } for i in qs]

        return Response(data)

    def post(self, request):
        user = request.user if request.user.is_authenticated else None
        project_id = request.data.get("project_id")
        
        user_projects = Project.objects.filter(
            Q(owner=user) | Q(memberships__user=user),
            is_archived=False
        ).distinct() if user else Project.objects.filter(is_archived=False)

        project = None
        if project_id:
            try:
                project = user_projects.filter(pk=int(project_id)).first()
            except (ValueError, TypeError):
                project = None
        if not project:
            project = user_projects.first()

        title = request.data.get("title", "").strip()

        if not title:
            return Response({"error": "Issue title is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not project:
            return Response({"error": "No accessible project exists. Please create a project first."}, status=status.HTTP_400_BAD_REQUEST)

        sprint_id = request.data.get("sprint_id")
        assignee_id = request.data.get("assignee_id")

        assignee = None
        if assignee_id:
            try:
                assignee = User.objects.filter(pk=int(assignee_id)).first()
            except (ValueError, TypeError):
                assignee = None

        sprint = None
        if sprint_id:
            try:
                sprint = project.sprints.filter(pk=int(sprint_id)).first()
            except (ValueError, TypeError):
                sprint = None

        # Safe Story Points parsing
        raw_pts = request.data.get("story_points", 3)
        try:
            story_points = int(raw_pts) if raw_pts not in [None, ""] else 3
        except (ValueError, TypeError):
            story_points = 3

        # Safe Date parsing
        raw_date = request.data.get("due_date")
        parsed_due_date = None
        if raw_date and str(raw_date).strip():
            raw_str = str(raw_date).strip()
            from datetime import datetime
            for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"]:
                try:
                    parsed_due_date = datetime.strptime(raw_str, fmt).date()
                    break
                except ValueError:
                    continue

        issue = Issue.objects.create(
            project=project,
            title=title,
            description=request.data.get("description", "").strip(),
            issue_type=request.data.get("issue_type", "TASK"),
            priority=request.data.get("priority", "MEDIUM"),
            status=request.data.get("status", "TODO"),
            story_points=story_points,
            assignee=assignee,
            sprint=sprint,
            reporter=user or project.owner,
            due_date=parsed_due_date,
            labels=request.data.get("labels", ""),
        )

        try:
            log = IssueAuditLog.objects.create(issue=issue, actor=user or project.owner, action="Created issue")
            from mongodb_engine.manager import mongo_manager
            mongo_manager.sync_issue(issue)
            mongo_manager.sync_audit_log(log)
        except Exception:
            pass

        return Response({
            "success": True,
            "message": "Issue created",
            "issue": {
                "id": issue.pk,
                "key": issue.key,
                "title": issue.title,
                "status": issue.status,
                "priority": issue.priority,
                "story_points": issue.story_points,
                "issue_type": issue.issue_type,
            }
        }, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name="dispatch")
class IssueMoveStatusAPI(APIView):
    """
    Drag and drop status movement API.
    """
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, pk):
        issue = get_object_or_404(Issue, pk=pk)
        user = request.user if request.user.is_authenticated else None
        new_status = request.data.get("status")
        target_sprint_id = request.data.get("sprint_id")
        old_status = issue.status

        if new_status:
            normalized_status = str(new_status).strip().upper().replace("-", "_").replace(" ", "_")
            if normalized_status in dict(Issue.STATUS_CHOICES):
                issue.status = normalized_status
            elif new_status in dict(Issue.STATUS_CHOICES):
                issue.status = new_status

        if target_sprint_id is not None:
            if target_sprint_id in ["backlog", "", 0]:
                issue.sprint = None
            else:
                issue.sprint = issue.project.sprints.filter(pk=target_sprint_id).first()

        issue.save()

        if old_status != issue.status:
            log = IssueAuditLog.objects.create(
                issue=issue,
                actor=user,
                action="Changed status",
                previous_value=old_status,
                new_value=issue.status,
            )
            try:
                from mongodb_engine.manager import mongo_manager
                mongo_manager.sync_issue(issue)
                mongo_manager.sync_audit_log(log)
            except Exception:
                pass

        if issue.sprint:
            # Synchronize completed points and recalculate sprint health
            done_pts = sum(i.story_points for i in issue.sprint.issues.filter(status="DONE"))
            issue.sprint.completed_points = done_pts
            issue.sprint.save(update_fields=["completed_points"])
            SprintHealthEngine.evaluate_sprint(issue.sprint)

        return Response({
            "message": "Status updated",
            "issue": {
                "id": issue.pk,
                "key": issue.key,
                "status": issue.status,
                "sprint_id": issue.sprint.pk if issue.sprint else None,
            }
        })


@method_decorator(csrf_exempt, name="dispatch")
class SubtaskToggleAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, subtask_pk):
        subtask = get_object_or_404(SubTask, pk=subtask_pk)
        subtask.is_completed = not subtask.is_completed
        subtask.save()
        return Response({"subtask_id": subtask.pk, "is_completed": subtask.is_completed})


@method_decorator(csrf_exempt, name="dispatch")
class WatcherToggleAPI(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    def post(self, request, pk):
        issue = get_object_or_404(Issue, pk=pk)
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response({"error": "User not authenticated"}, status=401)
        
        if issue.watchers.filter(pk=user.pk).exists():
            issue.watchers.remove(user)
            watching = False
        else:
            issue.watchers.add(user)
            watching = True
        return Response({"watching": watching, "total_watchers": issue.watchers.count()})
