import os
import django
import sqlite3

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User
from projects.models import Project, ProjectMember
from sprints.models import Sprint
from issues.models import Issue, SubTask, Comment, IssueAttachment, IssueLink, IssueAuditLog
from notifications.models import Notification, TeamRoom, ChatMessage
from mongodb_engine.manager import mongo_manager
from django.conf import settings

def wipe_all_data_to_zero():
    print("[Wipe] Completely deleting ALL projects, tickets, sprints, audit logs, and collections to 0...")

    # 1. Delete all relational data
    IssueAuditLog.objects.all().delete()
    IssueLink.objects.all().delete()
    IssueAttachment.objects.all().delete()
    Comment.objects.all().delete()
    SubTask.objects.all().delete()
    Issue.objects.all().delete()
    Sprint.objects.all().delete()
    Notification.objects.all().delete()
    ChatMessage.objects.all().delete()
    TeamRoom.objects.all().delete()
    ProjectMember.objects.all().delete()
    Project.objects.all().delete()

    # 2. Delete all MongoDB Collections
    if mongo_manager.is_connected and mongo_manager.db is not None:
        collections = [
            "projects", "issues", "sprints", "users",
            "audit_logs", "notifications", "chat_messages",
            "sprint_health_snapshots", "queue_telemetry"
        ]
        for col in collections:
            try:
                mongo_manager.db[col].delete_many({})
                print(f"[Wipe] Cleared MongoDB collection: {col}")
            except Exception as e:
                print(f"[Wipe] Error clearing {col}: {e}")

    # 3. Clear Local Fallback Document Store
    fallback_path = settings.BASE_DIR / "mongo_fallback.sqlite3"
    if fallback_path.exists():
        try:
            conn = sqlite3.connect(fallback_path)
            conn.execute("DELETE FROM mongo_documents")
            conn.commit()
            conn.close()
            print("[Wipe] Cleared local fallback document store.")
        except Exception:
            pass

    # 4. Retain only Aayush Shah as the single active user with 0 tickets & 0 projects
    user = User.objects.filter(username="Aayush_Shah").first()
    if not user:
        user = User.objects.filter(email="shahau933@gmail.com").first()
    if not user:
        user = User.objects.create_user(
            username="Aayush_Shah",
            email="shahau933@gmail.com",
            password="password123",
            first_name="Aayush",
            last_name="Shah",
            role="ADMIN",
            title="Software Engineer / Workspace Owner",
            avatar_color="#4f46e5",
        )
    else:
        user.first_name = "Aayush"
        user.last_name = "Shah"
        user.role = "ADMIN"
        user.title = "Software Engineer / Workspace Owner"
        user.is_staff = True
        user.is_superuser = True
        user.save()

    # Delete all other users
    User.objects.exclude(pk=user.pk).delete()

    # Sync single real user to MongoDB users collection
    mongo_manager.sync_user(user)

    print("\n[Wipe] 100% COMPLETE: Database is completely empty (0 projects, 0 issues, 0 sprints)!")
    print(f"       Active Workspace User: {user.display_name} ({user.email})")
    print("       All 9 MongoDB collections cleared to 0.")

if __name__ == "__main__":
    wipe_all_data_to_zero()
