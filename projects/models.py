from django.db import models
from django.conf import settings

class Project(models.Model):
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("COMPLETED", "Completed"),
        ("ARCHIVED", "Archived"),
    ]
    
    name = models.CharField(max_length=150)
    key = models.CharField(
        max_length=10,
        unique=True,
        help_text="Short project identifier eg. SPT"
    )
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_projects"
    )
    lead = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="led_projects"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE",
    )
    category = models.CharField(max_length=50, default="Software")
    avatar_color = models.CharField(max_length=20, default="#4f46e5")
    start_date = models.DateField(null=True, blank=True)
    target_date = models.DateField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_issues_count(self):
        return self.issues.count()

    @property
    def done_issues_count(self):
        return self.issues.filter(status="DONE").count()

    @property
    def open_issues_count(self):
        return self.issues.exclude(status="DONE").count()

    @property
    def progress_percentage(self):
        total = self.total_issues_count
        if total == 0:
            return 0
        return int((self.done_issues_count / total) * 100)

    @property
    def active_sprint(self):
        return self.sprints.filter(status="ACTIVE").first()

    def __str__(self):
        return f"{self.key} - {self.name}"

class ProjectMember(models.Model):
    ROLE_CHOICES = [
        ("OWNER", "Project Owner"),
        ("MANAGER", "Project Manager / Scrum Master"),
        ("DEVELOPER", "Software Developer"),
        ("TESTER", "QA / Tester"),
        ("VIEWER", "Viewer"),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="DEVELOPER")
    capacity_hours_per_week = models.IntegerField(default=40)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "user")

    def __str__(self):
        return f"{self.user.username} in {self.project.key} ({self.get_role_display()})"