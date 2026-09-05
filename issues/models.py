from django.db import models
from django.conf import settings
from projects.models import Project
from sprints.models import Sprint

class Issue(models.Model):
    TYPE_CHOICES = [
        ("STORY", "Story"),
        ("TASK", "Task"),
        ("BUG", "Bug"),
        ("EPIC", "Epic"),
        ("IMPROVEMENT", "Improvement"),
    ]

    PRIORITY_CHOICES = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
        ("CRITICAL", "Critical / Blocker"),
    ]

    STATUS_CHOICES = [
        ("BACKLOG", "Backlog"),
        ("TODO", "To Do"),
        ("IN_PROGRESS", "In Progress"),
        ("IN_REVIEW", "In Review"),
        ("BLOCKED", "Blocked"),
        ("DONE", "Done"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="issues")
    sprint = models.ForeignKey(Sprint, on_delete=models.SET_NULL, null=True, blank=True, related_name="issues")
    epic = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name="child_issues")
    
    key = models.CharField(max_length=20, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    issue_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="TASK")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="MEDIUM")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="TODO")
    story_points = models.IntegerField(default=3)
    
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_issues"
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reported_issues"
    )
    watchers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="watched_issues"
    )
    
    due_date = models.DateField(null=True, blank=True)
    labels = models.CharField(max_length=255, blank=True, default="")
    order_index = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order_index", "-updated_at"]
        unique_together = ("project", "key")

    def save(self, *args, **kwargs):
        if not self.key:
            last_issue = Issue.objects.filter(project=self.project).order_by("-id").first()
            if last_issue and "-" in last_issue.key:
                try:
                    last_num = int(last_issue.key.split("-")[-1])
                    self.key = f"{self.project.key}-{last_num + 1}"
                except ValueError:
                    self.key = f"{self.project.key}-1"
            else:
                self.key = f"{self.project.key}-1"
        super().save(*args, **kwargs)
        if self.sprint_id:
            try:
                done_pts = sum(i.story_points for i in self.sprint.issues.filter(status="DONE"))
                if self.sprint.completed_points != done_pts:
                    self.sprint.completed_points = done_pts
                    self.sprint.save(update_fields=["completed_points"])
            except Exception:
                pass


    @property
    def label_list(self):
        if not self.labels:
            return []
        return [l.strip() for l in self.labels.split(",") if l.strip()]

    @property
    def is_overdue(self):
        from datetime import date
        if self.due_date and self.status != "DONE":
            return self.due_date < date.today()
        return False

    @property
    def subtasks_total(self):
        return self.subtasks.count()

    @property
    def subtasks_completed(self):
        return self.subtasks.filter(is_completed=True).count()

    @property
    def subtasks_progress(self):
        if self.subtasks_total == 0:
            return 0
        return int((self.subtasks_completed / self.subtasks_total) * 100)

    def __str__(self):
        return f"[{self.key}] {self.title} ({self.get_status_display()})"


class SubTask(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="subtasks")
    title = models.CharField(max_length=255)
    is_completed = models.BooleanField(default=False)
    order_index = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.issue.key} subtask: {self.title}"


class Comment(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author.username} on {self.issue.key}"


class IssueAttachment(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="attachments")
    file_name = models.CharField(max_length=255)
    file_size = models.CharField(max_length=50, default="120 KB")
    file_url = models.CharField(max_length=500, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file_name} on {self.issue.key}"


class IssueLink(models.Model):
    LINK_CHOICES = [
        ("BLOCKS", "Blocks"),
        ("IS_BLOCKED_BY", "Is Blocked By"),
        ("RELATES_TO", "Relates To"),
        ("DUPLICATES", "Duplicates"),
    ]
    source_issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="outgoing_links")
    target_issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="incoming_links")
    link_type = models.CharField(max_length=30, choices=LINK_CHOICES, default="RELATES_TO")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("source_issue", "target_issue", "link_type")

    def __str__(self):
        return f"{self.source_issue.key} {self.link_type} {self.target_issue.key}"


class IssueAuditLog(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="audit_logs")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    previous_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.actor}: {self.action} on {self.issue.key}"
