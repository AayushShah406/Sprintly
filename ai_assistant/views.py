import json
from datetime import date, timedelta
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from projects.models import Project, ProjectMember
from sprints.models import Sprint
from issues.models import Issue, SubTask, Comment, IssueAuditLog
from accounts.models import User
from .service import sprintly_ai
from mongodb_engine.manager import mongo_manager

def get_current_user(request):
    if request.user.is_authenticated:
        return request.user
    return User.objects.first()

class AIChatAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = get_current_user(request)
        query = request.data.get("message", "").strip()
        context_data = request.data.get("context", {})

        if not query:
            return Response({"error": "Query message is required."}, status=status.HTTP_400_BAD_REQUEST)

        result = sprintly_ai.ask_natural_language(query, context_data, user)
        return Response(result)


class AISprintPlannerAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = get_current_user(request)
        project_id = request.data.get("project_id")
        project = Project.objects.filter(pk=project_id).first() if project_id else Project.objects.filter(is_archived=False).first()

        if not project:
            return Response({"error": "No accessible project found."}, status=status.HTTP_404_NOT_FOUND)

        capacity = request.data.get("capacity")
        result = sprintly_ai.plan_sprint(project, user, target_capacity=int(capacity) if capacity else None)
        return Response(result)


class AISprintRiskAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = get_current_user(request)
        sprint_id = request.data.get("sprint_id")
        sprint = Sprint.objects.filter(pk=sprint_id).first() if sprint_id else Sprint.objects.filter(status="ACTIVE").first()

        if not sprint:
            return Response({
                "success": True,
                "sprint_name": "No Active Sprint",
                "health_score": 100,
                "risk_level": "LOW",
                "detected_risks": ["No active sprint is currently running in this workspace."],
                "recommendations": ["Create a sprint and assign backlog issues to begin tracking sprint risk."],
            })

        result = sprintly_ai.analyze_sprint_risk(sprint, user)
        return Response(result)


class AIIssueImprovementAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = get_current_user(request)
        title = request.data.get("title", "").strip()
        description = request.data.get("description", "").strip()

        if not title:
            return Response({"error": "Title is required."}, status=status.HTTP_400_BAD_REQUEST)

        result = sprintly_ai.improve_issue(title, description, user)
        return Response(result)


class AIIssueBreakdownAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = get_current_user(request)
        issue_id = request.data.get("issue_id")
        issue = get_object_or_404(Issue, pk=issue_id)

        subtasks = sprintly_ai.breakdown_issue(issue, user)
        return Response({"success": True, "issue_key": issue.key, "suggested_subtasks": subtasks})


class AIAcceptanceCriteriaAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = get_current_user(request)
        issue_id = request.data.get("issue_id")
        issue = get_object_or_404(Issue, pk=issue_id)

        criteria = sprintly_ai.generate_acceptance_criteria(issue, user)
        return Response({"success": True, "issue_key": issue.key, "acceptance_criteria": criteria})


class AIPrioritySuggestionAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = get_current_user(request)
        issue_id = request.data.get("issue_id")
        issue = get_object_or_404(Issue, pk=issue_id)

        result = sprintly_ai.suggest_priority(issue, user)
        return Response({"success": True, "issue_key": issue.key, **result})


class AIStoryPointEstimationAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = get_current_user(request)
        issue_id = request.data.get("issue_id")
        issue = get_object_or_404(Issue, pk=issue_id)

        result = sprintly_ai.estimate_story_points(issue, user)
        return Response({"success": True, "issue_key": issue.key, **result})


class AIFindSimilarAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = get_current_user(request)
        title = request.data.get("title", "").strip()
        project_id = request.data.get("project_id")
        project = Project.objects.filter(pk=project_id).first() if project_id else Project.objects.filter(is_archived=False).first()

        if not project or not title:
            return Response({"similar_issues": []})

        exclude_id = request.data.get("exclude_id")
        results = sprintly_ai.find_similar_issues(title, project, user, exclude_id=int(exclude_id) if exclude_id else None)
        return Response({"success": True, "similar_issues": results})


class AIProjectSummaryAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = get_current_user(request)
        project_id = request.data.get("project_id")
        project = Project.objects.filter(pk=project_id).first() if project_id else Project.objects.filter(is_archived=False).first()

        if not project:
            return Response({"error": "No project found."}, status=status.HTTP_404_NOT_FOUND)

        result = sprintly_ai.summarize_project(project, user)
        return Response(result)


class AIStandupGeneratorAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = get_current_user(request)
        result = sprintly_ai.generate_standup(user)
        return Response(result)


class AIDailyWorkAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = get_current_user(request)
        recs = sprintly_ai.recommend_daily_work(user)
        return Response({"success": True, "recommendations": recs})


class AIApplyActionAPI(APIView):
    """
    Safely executes user-confirmed AI operations.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        user = get_current_user(request)
        action_type = request.data.get("action_type")
        payload = request.data.get("payload", {})

        # 1. Apply Sprint Plan
        if action_type == "APPLY_SPRINT_PLAN":
            issue_ids = payload.get("issue_ids", [])
            sprint_id = payload.get("sprint_id")
            project_id = payload.get("project_id")
            sprint = Sprint.objects.filter(pk=sprint_id).first() if sprint_id else None
            
            if not sprint and project_id:
                proj = Project.objects.filter(pk=project_id).first()
                if proj:
                    sprint = proj.sprints.filter(status__in=["ACTIVE", "PLANNING"]).first()
                    if not sprint:
                        next_num = (proj.sprints.count() or 0) + 1
                        sprint = Sprint.objects.create(
                            project=proj,
                            name=f"Sprint {next_num}",
                            sprint_number=next_num,
                            status="PLANNING",
                            goal="AI Recommended Sprint Plan",
                            start_date=date.today(),
                            end_date=date.today() + timedelta(days=14)
                        )

            if not sprint and issue_ids:
                first_issue = Issue.objects.filter(pk=issue_ids[0]).first()
                if first_issue:
                    sprint = first_issue.project.sprints.filter(status__in=["ACTIVE", "PLANNING"]).first()
                    if not sprint:
                        next_num = (first_issue.project.sprints.count() or 0) + 1
                        sprint = Sprint.objects.create(
                            project=first_issue.project,
                            name=f"Sprint {next_num}",
                            sprint_number=next_num,
                            status="PLANNING",
                            goal="AI Recommended Sprint Plan",
                            start_date=date.today(),
                            end_date=date.today() + timedelta(days=14)
                        )

            if not sprint:
                proj = Project.objects.filter(is_archived=False).first()
                if proj:
                    sprint = proj.sprints.filter(status__in=["ACTIVE", "PLANNING"]).first()
                    if not sprint:
                        sprint = Sprint.objects.create(
                            project=proj,
                            name="Sprint 1",
                            sprint_number=1,
                            status="PLANNING",
                            goal="AI Recommended Sprint Plan",
                            start_date=date.today(),
                            end_date=date.today() + timedelta(days=14)
                        )
                    if not issue_ids:
                        issue_ids = list(proj.issues.filter(sprint__isnull=True).values_list("id", flat=True)[:5])

            if sprint:
                count = Issue.objects.filter(id__in=issue_ids).update(sprint=sprint)
                for issue in Issue.objects.filter(id__in=issue_ids):
                    try:
                        log = IssueAuditLog.objects.create(issue=issue, actor=user or sprint.project.owner, action=f"Assigned to {sprint.name} via AI Plan")
                        mongo_manager.sync_issue(issue)
                        mongo_manager.sync_audit_log(log)
                    except Exception:
                        pass
                try:
                    sprint.total_committed_points = sum(i.story_points for i in sprint.issues.all())
                    sprint.save()
                    mongo_manager.sync_sprint(sprint)
                except Exception:
                    pass
                return Response({"success": True, "message": f"Successfully applied sprint plan: Added {count} issue(s) to {sprint.name}."})
            return Response({"error": "Target project or sprint not found."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Apply Subtasks Creation
        elif action_type == "CREATE_SUBTASKS":
            issue_id = payload.get("issue_id")
            subtasks = payload.get("subtasks", [])
            issue = get_object_or_404(Issue, pk=issue_id)

            created_count = 0
            for st_title in subtasks:
                if st_title.strip():
                    SubTask.objects.create(issue=issue, title=st_title.strip())
                    created_count += 1

            log = IssueAuditLog.objects.create(issue=issue, actor=user, action=f"Created {created_count} subtasks via AI")
            mongo_manager.sync_issue(issue)
            mongo_manager.sync_audit_log(log)
            return Response({"success": True, "message": f"Created {created_count} subtasks for {issue.key}."})

        # 3. Apply Priority Change
        elif action_type == "CHANGE_PRIORITY":
            issue_id = payload.get("issue_id")
            new_priority = payload.get("priority")
            issue = get_object_or_404(Issue, pk=issue_id)
            old_p = issue.priority
            issue.priority = new_priority
            issue.save()

            log = IssueAuditLog.objects.create(issue=issue, actor=user, action="Updated priority via AI", previous_value=old_p, new_value=new_priority)
            mongo_manager.sync_issue(issue)
            mongo_manager.sync_audit_log(log)
            return Response({"success": True, "message": f"Updated {issue.key} priority to {new_priority}."})

        # 4. Apply Story Points
        elif action_type in ["UPDATE_POINTS", "ESTIMATE_POINTS"]:
            issue_id = payload.get("issue_id")
            points = payload.get("points") or payload.get("story_points")
            issue = get_object_or_404(Issue, pk=issue_id)
            old_pts = issue.story_points
            issue.story_points = int(points)
            issue.save()
            try:
                log = IssueAuditLog.objects.create(issue=issue, actor=user, action="Updated points via AI", previous_value=str(old_pts), new_value=str(points))
                mongo_manager.sync_issue(issue)
                mongo_manager.sync_audit_log(log)
            except Exception:
                pass
            return Response({"success": True, "message": f"Updated {issue.key} story points to {points} pts."})

        # 5. Apply Work Allocation Matrix
        elif action_type == "APPLY_WORK_ALLOCATION":
            allocations = payload.get("allocations", [])
            updated_count = 0
            for alloc in allocations:
                issue_id = alloc.get("issue_id")
                assignee_id = alloc.get("assigned_to", {}).get("id") if isinstance(alloc.get("assigned_to"), dict) else alloc.get("assignee_id")
                if issue_id and assignee_id:
                    issue = Issue.objects.filter(pk=issue_id).first()
                    target_user = User.objects.filter(pk=assignee_id).first()
                    if issue and target_user:
                        issue.assignee = target_user
                        issue.save()
                        try:
                            log = IssueAuditLog.objects.create(issue=issue, actor=user or target_user, action=f"Allocated to {target_user.display_name} via AI Work Allocation")
                            mongo_manager.sync_issue(issue)
                            mongo_manager.sync_audit_log(log)
                        except Exception:
                            pass
                        updated_count += 1
            return Response({"success": True, "message": f"Successfully allocated {updated_count} task(s) to team members."})

        return Response({"error": "Unsupported action type."}, status=status.HTTP_400_BAD_REQUEST)


class AIAllocateWorkAPI(APIView):
    """
    Intelligently balances workload and suggests teammate assignments.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        user = get_current_user(request)
        project_id = request.data.get("project_id")
        project = None
        if project_id:
            try:
                project = Project.objects.filter(pk=int(project_id)).first()
            except (ValueError, TypeError):
                project = None
        if not project:
            project = Project.objects.filter(is_archived=False).first()

        if not project:
            return Response({"error": "No project found."}, status=status.HTTP_400_BAD_REQUEST)

        result = sprintly_ai.allocate_team_work(project, user)
        return Response(result)
