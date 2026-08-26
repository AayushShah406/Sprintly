from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from sprints.models import Sprint
from projects.models import Project
from issues.models import Issue
from .health_service import SprintHealthEngine
from mongodb_engine.manager import mongo_manager

class SprintHealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, sprint_id=None):
        if sprint_id:
            sprint = get_object_or_404(Sprint, pk=sprint_id)
        else:
            # Get default active sprint or latest sprint
            sprint = Sprint.objects.filter(status="ACTIVE").first()
            if not sprint:
                sprint = Sprint.objects.first()

        if not sprint:
            return Response({"error": "No sprints found."}, status=status.HTTP_404_NOT_FOUND)

        health_data = SprintHealthEngine.evaluate_sprint(sprint)
        return Response(health_data)


class AnalyticsOverviewView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        project_id = request.query_params.get("project_id")
        
        sprints_qs = Sprint.objects.all()
        issues_qs = Issue.objects.all()
        
        if project_id:
            sprints_qs = sprints_qs.filter(project_id=project_id)
            issues_qs = issues_qs.filter(project_id=project_id)

        active_sprint = sprints_qs.filter(status="ACTIVE").first()
        active_health = None
        if active_sprint:
            active_health = SprintHealthEngine.evaluate_sprint(active_sprint)

        # Calculate workspace velocity across past completed sprints
        completed_sprints = list(sprints_qs.filter(status="COMPLETED").order_by("sprint_number")[:6])
        velocity_trend = []
        for cs in completed_sprints:
            pts = cs.completed_points or sum(i.story_points for i in cs.issues.filter(status="DONE"))
            velocity_trend.append({
                "sprint": cs.name,
                "completed_points": pts,
                "committed_points": cs.total_committed_points or pts,
            })

        # Issue status breakdown
        status_counts = {
            "BACKLOG": issues_qs.filter(status="BACKLOG").count(),
            "TODO": issues_qs.filter(status="TODO").count(),
            "IN_PROGRESS": issues_qs.filter(status="IN_PROGRESS").count(),
            "IN_REVIEW": issues_qs.filter(status="IN_REVIEW").count(),
            "DONE": issues_qs.filter(status="DONE").count(),
        }

        # Priority breakdown
        priority_counts = {
            "CRITICAL": issues_qs.filter(priority="CRITICAL").count(),
            "HIGH": issues_qs.filter(priority="HIGH").count(),
            "MEDIUM": issues_qs.filter(priority="MEDIUM").count(),
            "LOW": issues_qs.filter(priority="LOW").count(),
        }

        return Response({
            "active_sprint_health": active_health,
            "velocity_trend": velocity_trend,
            "status_counts": status_counts,
            "priority_counts": priority_counts,
            "total_issues": issues_qs.count(),
            "total_sprints": sprints_qs.count(),
        })


class HistoricalHealthLogsView(APIView):
    """
    Fetches immutable health snapshots directly from MongoDB document store.
    """
    permission_classes = [AllowAny]

    def get(self, request, sprint_id):
        docs = mongo_manager.find_documents(
            "sprint_health_snapshots",
            query={"sprint_id": int(sprint_id)},
            limit=20
        )
        return Response(docs)
