from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from accounts.models import User
from projects.models import Project
from notifications.models import TeamRoom, ChatMessage, Notification

class TeamChatAndNotificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="chat_user",
            email="chat_user@sprintly.io",
            password="Password123!",
            first_name="Alex",
            last_name="Rivers"
        )
        self.client.force_authenticate(user=self.user)
        self.project = Project.objects.create(
            name="Chat Project",
            key="CHP",
            owner=self.user,
            lead=self.user
        )
        self.room = TeamRoom.objects.create(
            project=self.project,
            name="dev-team",
            description="Engineering chat room"
        )

    def test_team_chat_page_loads(self):
        url = reverse("notifications:team_chat")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "PROJECT CHANNELS")

    def test_post_and_get_room_messages(self):
        url = reverse("notifications:room_messages_api", kwargs={"room_id": self.room.id})
        
        # Post message
        res_post = self.client.post(url, {"content": "Hello team, deploying to staging!"}, format="json")
        self.assertEqual(res_post.status_code, 201)
        self.assertTrue(res_post.json().get("success"))

        # Get messages
        res_get = self.client.get(url)
        self.assertEqual(res_get.status_code, 200)
        data = res_get.json()
        self.assertEqual(len(data.get("messages", [])), 1)
        self.assertEqual(data["messages"][0]["content"], "Hello team, deploying to staging!")
