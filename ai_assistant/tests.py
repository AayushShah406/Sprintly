from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from accounts.models import User
from projects.models import Project, ProjectMember
from sprints.models import Sprint
from issues.models import Issue, SubTask
from ai_assistant.service import sprintly_ai

class SprintlyAIEngineTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="test_ai_user",
            email="ai_user@sprintly.io",
            password="password123",
            first_name="Test",
            last_name="Engineer"
        )
        self.project = Project.objects.create(
            name="AI Test Platform",
            key="AIT",
            owner=self.user,
            lead=self.user
        )
        ProjectMember.objects.create(project=self.project, user=self.user, role="OWNER", capacity_hours_per_week=40)
        self.sprint = Sprint.objects.create(
            project=self.project,
            name="Sprint 1",
            sprint_number=1,
            status="ACTIVE",
            goal="Deliver AI capabilities"
        )
        self.issue1 = Issue.objects.create(
            project=self.project,
            title="Implement OAuth2 Authentication",
            issue_type="STORY",
            priority="HIGH",
            story_points=5,
            reporter=self.user,
            assignee=self.user
        )
        self.issue2 = Issue.objects.create(
            project=self.project,
            title="Fix Database Connection Timeout",
            issue_type="BUG",
            priority="CRITICAL",
            story_points=3,
            reporter=self.user,
            assignee=self.user
        )

    def test_sprint_planner_api(self):
        url = reverse("ai_assistant:plan_sprint")
        response = self.client.post(url, {"project_id": self.project.id, "capacity": 20}, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertIn("recommended_issues", data)

    def test_sprint_risk_analysis_api(self):
        url = reverse("ai_assistant:analyze_sprint")
        response = self.client.post(url, {"sprint_id": self.sprint.id}, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertIn("health_score", data)
        self.assertIn("risk_level", data)

    def test_issue_improvement_api(self):
        url = reverse("ai_assistant:improve_issue")
        response = self.client.post(url, {"title": "login is broken", "description": "errors on submit"}, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertIn("suggestion", data)

    def test_acceptance_criteria_and_breakdown(self):
        ac_url = reverse("ai_assistant:acceptance_criteria")
        response = self.client.post(ac_url, {"issue_id": self.issue1.id}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("success"))

        bd_url = reverse("ai_assistant:breakdown_issue")
        response = self.client.post(bd_url, {"issue_id": self.issue1.id}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("success"))

    def test_apply_action_creates_subtasks(self):
        url = reverse("ai_assistant:apply_action")
        payload = {
            "action_type": "CREATE_SUBTASKS",
            "payload": {
                "issue_id": self.issue1.id,
                "subtasks": ["Write Unit Tests", "Implement Handler", "Update Documentation"]
            }
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("success"))
        self.assertEqual(SubTask.objects.filter(issue=self.issue1).count(), 3)

    def test_ai_allocate_work_and_apply(self):
        # 1. Test AI allocation generation
        url_alloc = reverse("ai_assistant:allocate_work")
        res_alloc = self.client.post(url_alloc, {"project_id": self.project.id}, format="json")
        self.assertEqual(res_alloc.status_code, 200)
        data = res_alloc.json()
        self.assertTrue(data.get("success"))
        self.assertIn("allocations", data)

        # 2. Test applying AI allocation
        url_apply = reverse("ai_assistant:apply_action")
        res_apply = self.client.post(url_apply, {
            "action_type": "APPLY_WORK_ALLOCATION",
            "payload": {
                "allocations": data.get("allocations", [])
            }
        }, format="json")
        self.assertEqual(res_apply.status_code, 200)
        self.assertTrue(res_apply.json().get("success"))

