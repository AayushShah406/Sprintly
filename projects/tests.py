from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from accounts.models import User
from projects.models import Project, ProjectMember
from sprints.models import Sprint
from issues.models import Issue

class ProjectTeamManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username="owner_user",
            email="owner@sprintly.io",
            password="Password123!",
            first_name="Workspace",
            last_name="Owner"
        )
        self.client.force_authenticate(user=self.owner)
        self.project = Project.objects.create(
            name="Sprintly Enterprise Core",
            key="SPR",
            owner=self.owner,
            lead=self.owner
        )
        ProjectMember.objects.create(project=self.project, user=self.owner, role="OWNER")

    def test_invite_new_teammate_creates_user_and_membership(self):
        team_url = reverse("projects:team", kwargs={"pk": self.project.pk})
        res = self.client.post(team_url, {
            "new_teammate_first_name": "Sarah",
            "new_teammate_last_name": "Connor",
            "new_teammate_email": "sarah.connor@sprintly.io",
            "new_teammate_title": "Senior QA Engineer",
            "new_teammate_role": "TESTER",
            "new_teammate_capacity": "35",
        })
        self.assertEqual(res.status_code, 302)

        sarah = User.objects.filter(email="sarah.connor@sprintly.io").first()
        self.assertIsNotNone(sarah)
        self.assertEqual(sarah.first_name, "Sarah")
        self.assertEqual(sarah.last_name, "Connor")

        pm = ProjectMember.objects.filter(project=self.project, user=sarah).first()
        self.assertIsNotNone(pm)
        self.assertEqual(pm.role, "TESTER")
        self.assertEqual(pm.capacity_hours_per_week, 35)

    def test_remove_teammate_from_project(self):
        teammate = User.objects.create_user(
            username="dev_member",
            email="dev@sprintly.io",
            password="Password123!"
        )
        pm = ProjectMember.objects.create(project=self.project, user=teammate, role="DEVELOPER")
        
        team_url = reverse("projects:team", kwargs={"pk": self.project.pk})
        res = self.client.post(team_url, {
            "remove_member_id": pm.id
        })
        self.assertEqual(res.status_code, 302)
        self.assertFalse(ProjectMember.objects.filter(id=pm.id).exists())

    def test_create_sprint_from_project_hub(self):
        url = reverse("projects:backlog", kwargs={"pk": self.project.pk})
        res = self.client.post(url, {
            "sprint_name": "Sprint 1 - Core MVP",
            "sprint_goal": "Deliver auth and dashboard",
            "duration_days": "14"
        })
        self.assertEqual(res.status_code, 302)
        sprint = Sprint.objects.filter(project=self.project, name="Sprint 1 - Core MVP").first()
        self.assertIsNotNone(sprint)
        self.assertEqual(sprint.goal, "Deliver auth and dashboard")

    def test_create_epic_from_roadmap(self):
        url = reverse("projects:roadmap", kwargs={"pk": self.project.pk})
        res = self.client.post(url, {
            "epic_title": "Enterprise Security and IAM",
            "epic_description": "Implement RBAC and OAuth2",
            "epic_priority": "CRITICAL"
        })
        self.assertEqual(res.status_code, 302)
        epic = Issue.objects.filter(project=self.project, issue_type="EPIC").first()
        self.assertIsNotNone(epic)
        self.assertEqual(epic.title, "Enterprise Security and IAM")
        self.assertEqual(epic.priority, "CRITICAL")
