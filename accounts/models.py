import random
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = [
        ("ADMIN", "Administrator"),
        ("MANAGER", "Project Manager / Scrum Master"),
        ("DEVELOPER", "Software Engineer"),
        ("TESTER", "QA / Test Engineer"),
        ("VIEWER", "Stakeholder / Viewer"),
    ]
    
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default="DEVELOPER")
    avatar_color = models.CharField(max_length=20, default="#4f46e5")
    title = models.CharField(max_length=100, blank=True, default="Software Engineer")
    theme_preference = models.CharField(max_length=10, default="light", choices=[("light", "Light"), ("dark", "Dark")])
    timezone = models.CharField(max_length=50, default="UTC")
    email_notifications_enabled = models.BooleanField(default=True)
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def display_name(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full if full else self.username

    @property
    def initials(self):
        first = self.first_name[0].upper() if self.first_name else ""
        last = self.last_name[0].upper() if self.last_name else ""
        if not first and not last:
            return self.username[:2].upper()
        return f"{first}{last}"

    def __str__(self):
        return f"{self.display_name} ({self.get_role_display()})"


class EmailOTP(models.Model):
    PURPOSE_CHOICES = [
        ("SIGNUP", "Signup Email Verification"),
        ("LOGIN", "Login Verification (2FA)"),
        ("RESET", "Password Reset"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_otps"
    )
    otp_code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default="SIGNUP")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    @classmethod
    def create_otp(cls, user, purpose="SIGNUP", validity_minutes=10):
        """Generates a fresh 6-digit cryptographically random OTP and marks previous unused OTPs as expired."""
        cls.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)
        code = f"{random.randint(100000, 999999):06d}"
        expires = timezone.now() + timedelta(minutes=validity_minutes)
        return cls.objects.create(
            user=user,
            otp_code=code,
            purpose=purpose,
            expires_at=expires,
            is_used=False,
            attempts=0
        )

    def is_valid(self):
        return not self.is_used and timezone.now() <= self.expires_at and self.attempts < 5

    def __str__(self):
        return f"OTP({self.purpose}) for {self.user.username} - Valid: {self.is_valid()}"


class RefreshToken(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="refresh_tokens"
    )
    jti = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Token for {self.user.username}"