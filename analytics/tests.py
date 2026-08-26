from datetime import date, timedelta
from django.test import TestCase
from accounts.models import User
from projects.models import Project
from sprints.models import Sprint
from issues.models import Issue
from analytics.health_service import SprintHealthEngine

class SprintHealthEngineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sarah", email="sarah@sprintly.io", password="password123")
        self.project = Project.objects.create(name="Analytics Core", key="ANA", owner=self.user)
        today = date.today()
        self.sprint = Sprint.objects.create(
            project=self.project,
            name="Health Sprint",
            sprint_number=1,
            status="ACTIVE",
            start_date=today - timedelta(days=5),
            end_date=today + timedelta(days=9),
            total_committed_points=20,
        )
        Issue.objects.create(project=self.project, sprint=self.sprint, title="Task 1", status="DONE", story_points=8, assignee=self.user)
        Issue.objects.create(project=self.project, sprint=self.sprint, title="Task 2", status="IN_PROGRESS", story_points=5, assignee=self.user)
        Issue.objects.create(project=self.project, sprint=self.sprint, title="Task 3", status="TODO", story_points=7, assignee=self.user)

    def test_sprint_health_calculation(self):
        health = SprintHealthEngine.evaluate_sprint(self.sprint)
        self.assertIn("health_score", health)
        self.assertIn("status_label", health)
        self.assertIn("burndown_score", health)
        self.assertIn("completion_probability", health)
        self.assertIn("diagnostics", health)
        self.assertGreaterEqual(health["health_score"], 0)
        self.assertLessEqual(health["health_score"], 100)
        self.assertEqual(health["completed_points"], 8)
        self.assertEqual(health["remaining_points"], 12)
