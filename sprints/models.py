from django.db import models
from projects.models import Project

class Sprint(models.Model):
    STATUS_CHOICES = [
        ("PLANNING", "Planning / Future"),
        ("ACTIVE", "Active"),
        ("COMPLETED", "Completed"),
        ("CLOSED", "Closed"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="sprints")
    name = models.CharField(max_length=150)
    sprint_number = models.PositiveIntegerField(default=1)
    goal = models.TextField(blank=True, help_text="Core objective and deliverables for this sprint")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PLANNING")
    
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    total_committed_points = models.IntegerField(default=0)
    completed_points = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-sprint_number", "-created_at"]

    def __str__(self):
        return f"{self.project.key} - {self.name} ({self.status})"

    @property
    def issues_count(self):
        return self.issues.count()

    @property
    def remaining_points(self):
        total = sum(i.story_points for i in self.issues.all())
        done = sum(i.story_points for i in self.issues.filter(status="DONE"))
        return max(0, total - done)
