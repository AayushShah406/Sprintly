from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from accounts.models import User
from projects.models import Project
from sprints.models import Sprint
from issues.models import Issue, SubTask

class IssueAndKanbanTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="alex", email="alex@sprintly.io", password="password123")
        self.project = Project.objects.create(name="Platform Core", key="PLT", owner=self.user)
        self.sprint = Sprint.objects.create(project=self.project, name="Sprint 1", sprint_number=1, status="ACTIVE")
        self.issue = Issue.objects.create(
            project=self.project,
            sprint=self.sprint,
            title="Deploy Workload Balancing",
            status="TODO",
            priority="HIGH",
            story_points=5,
            assignee=self.user,
        )

    def test_issue_creation_and_key_generation(self):
        self.assertEqual(self.issue.key, "PLT-1")
        self.assertEqual(self.issue.status, "TODO")
        
        issue2 = Issue.objects.create(
            project=self.project,
            title="Second Ticket",
            status="BACKLOG"
        )
        self.assertEqual(issue2.key, "PLT-2")

    def test_create_issue_api_with_custom_date_format(self):
        url = reverse("issues:api_list_create")
        res = self.client.post(url, {
            "title": "Implement Feature 1: User Data Export",
            "description": "Export personal data in CSV format",
            "project_id": self.project.id,
            "issue_type": "TASK",
            "priority": "MEDIUM",
            "story_points": "5",
            "due_date": "28-08-2026",
            "labels": "frontend, backend, export, ui"
        }, format="json")
        self.assertEqual(res.status_code, 201)
        created_issue = Issue.objects.get(title="Implement Feature 1: User Data Export")
        self.assertEqual(str(created_issue.due_date), "2026-08-28")
        self.assertEqual(created_issue.story_points, 5)

    def test_drag_and_drop_move_api(self):
        res = self.client.post(reverse("issues:api_move_status", kwargs={"pk": self.issue.pk}), {
            "status": "IN_PROGRESS"
        }, format="json")
        self.assertEqual(res.status_code, 200)
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.status, "IN_PROGRESS")

    def test_subtask_progress(self):
        st1 = SubTask.objects.create(issue=self.issue, title="Subtask 1", is_completed=True)
        st2 = SubTask.objects.create(issue=self.issue, title="Subtask 2", is_completed=False)
        self.assertEqual(self.issue.subtasks_total, 2)
        self.assertEqual(self.issue.subtasks_completed, 1)
        self.assertEqual(self.issue.subtasks_progress, 50)
