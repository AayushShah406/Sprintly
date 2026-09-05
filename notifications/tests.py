from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from accounts.models import User
from projects.models import Project, ProjectMember
from notifications.models import Notification

class NotificationAppTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="notif_user",
            email="notif_user@sprintly.io",
            password="Password123!",
            first_name="Alex",
            last_name="Rivers"
        )
        self.client.force_login(self.user)
        self.client.force_authenticate(user=self.user)
        self.project = Project.objects.create(
            name="Notification Project",
            key="NOTIF",
            owner=self.user,
            lead=self.user
        )
        ProjectMember.objects.create(project=self.project, user=self.user, role="OWNER")
        self.notif = Notification.objects.create(
            recipient=self.user,
            title="Sprint 1 Started",
            message="Sprint 1 is now active.",
            notification_type="SPRINT_STARTED"
        )

    def test_notification_inbox_loads(self):
        url = reverse("notifications:inbox")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Sprint 1 Started")

    def test_notification_mark_read(self):
        url = reverse("notifications:mark_read", kwargs={"pk": self.notif.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 302)
        self.notif.refresh_from_db()
        self.assertTrue(self.notif.is_read)

    def test_notification_delete(self):
        url = reverse("notifications:delete", kwargs={"pk": self.notif.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 302)
        self.assertFalse(Notification.objects.filter(pk=self.notif.pk).exists())

    def test_notification_api_list(self):
        url = reverse("notifications:api")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("notifications", data)
        self.assertIn("unread_count", data)
