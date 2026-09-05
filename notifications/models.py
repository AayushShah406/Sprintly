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
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name="invitation_notifications")
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default="SYSTEM")
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    invitation_role = models.CharField(max_length=50, blank=True, default="DEVELOPER")
    invitation_status = models.CharField(
        max_length=20,
        default="PENDING",
        choices=[("PENDING", "Pending"), ("ACCEPTED", "Accepted"), ("DECLINED", "Declined")]
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.title}"

