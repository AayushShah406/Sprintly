from django.db import models
from sprints.models import Sprint
from config.crypto_utils import compute_sha256_hash

class SprintHealthSnapshot(models.Model):
    STATUS_CHOICES = [
        ("HEALTHY", "Healthy (Optimal Velocity)"),
        ("MODERATE_RISK", "Moderate Risk (Attention Required)"),
        ("CRITICAL_RISK", "Critical Risk (Sprint Target in Jeopardy)"),
    ]

    sprint = models.ForeignKey(Sprint, on_delete=models.CASCADE, related_name="health_snapshots")
    health_score = models.IntegerField(default=100, help_text="Composite score 0-100")
    status_label = models.CharField(max_length=30, choices=STATUS_CHOICES, default="HEALTHY")
    
    burndown_score = models.IntegerField(default=100)
    scope_creep_score = models.IntegerField(default=100)
    bottleneck_score = models.IntegerField(default=100)
    workload_score = models.IntegerField(default=100)
    completion_probability = models.IntegerField(default=95)
    
    diagnostics_json = models.TextField(blank=True, default="[]")
    sha256_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        self.sha256_hash = compute_sha256_hash({
            "sprint_id": self.sprint.pk,
            "health_score": self.health_score,
            "status": self.status_label,
            "burndown": self.burndown_score,
            "prob": self.completion_probability,
        })
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sprint.name} Health: {self.health_score}/100 ({self.status_label})"
