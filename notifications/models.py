from django.db import models
from django.conf import settings
from projects.models import Project

class Notification(models.Model):
    TYPE_CHOICES = [
        ("ASSIGNMENT", "Issue Assigned"),
        ("STATUS_CHANGE", "Status Changed"),
        ("COMMENT", "New Comment"),
        ("MENTION", "User Mentioned"),
        ("SPRINT_STARTED", "Sprint Started"),
        ("SPRINT_COMPLETED", "Sprint Completed"),
        ("DUE_DATE_APPROACHING", "Due Date Approaching"),
        ("PROJECT_INVITATION", "Project Invitation"),
        ("SYSTEM", "System Update"),
    ]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default="SYSTEM")
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.title}"


class TeamRoom(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="chat_rooms")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"#{self.name} ({self.project.key})"


class ChatMessage(models.Model):
    room = models.ForeignKey(TeamRoom, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author.username}: {self.content[:30]}..."
