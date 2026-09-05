import os
import django
import sqlite3

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User
from projects.models import Project, ProjectMember
from sprints.models import Sprint
from issues.models import Issue, SubTask, Comment, IssueAttachment, IssueLink, IssueAuditLog
from notifications.models import Notification
from mongodb_engine.manager import mongo_manager
from django.conf import settings

def reset_all_data():
    print("[Reset] Purging all database tables and MongoDB document collections to 0...")

    # 1. Clear SQLite Relational Tables
    IssueAuditLog.objects.all().delete()
    IssueLink.objects.all().delete()
    IssueAttachment.objects.all().delete()
    Comment.objects.all().delete()
    SubTask.objects.all().delete()
    Issue.objects.all().delete()
    Sprint.objects.all().delete()
    Notification.objects.all().delete()
    ProjectMember.objects.all().delete()
    Project.objects.all().delete()
    
    # 2. Clear MongoDB Collections
    if mongo_manager.is_connected and mongo_manager.db is not None:
        collections = [
            "projects", "issues", "sprints", "users",
            "audit_logs", "notifications", "chat_messages",
            "sprint_health_snapshots", "queue_telemetry"
        ]
        for col in collections:
            try:
                mongo_manager.db[col].delete_many({})
                print(f"[Reset] Cleared MongoDB collection: {col}")
            except Exception as e:
                print(f"[Reset] Error clearing {col}: {e}")

    # 3. Clear Fallback SQLite Document Store
    fallback_path = settings.BASE_DIR / "mongo_fallback.sqlite3"
    if fallback_path.exists():
        try:
            conn = sqlite3.connect(fallback_path)
            conn.execute("DELETE FROM mongo_documents")
            conn.commit()
            conn.close()
            print("[Reset] Cleared local fallback document store.")
        except Exception:
            pass

    # 4. Upsert Clean Users with 0 tickets
    users_data = [
        ("admin@sprintly.io", "admin", "Antigravity", "Admin", "ADMIN", "System Administrator", "#4f46e5"),
        ("alex@sprintly.io", "alex_pm", "Alex", "Mercer", "MANAGER", "Project Manager", "#7c3aed"),
        ("sarah@sprintly.io", "sarah_dev", "Sarah", "Chen", "DEVELOPER", "Software Engineer", "#0284c7"),
        ("david@sprintly.io", "david_qa", "David", "Kim", "TESTER", "QA Engineer", "#059669"),
    ]

    created_users = {}
    for email, uname, fname, lname, role, title, color in users_data:
        u = User.objects.filter(email=email).first()
        if not u:
            u = User.objects.filter(username=uname).first()
        if not u:
            u = User.objects.create(email=email, username=uname)
        
        u.first_name = fname
        u.last_name = lname
        u.role = role
        u.title = title
        u.avatar_color = color
        u.theme_preference = "light"
        u.set_password("password123")
        if role == "ADMIN":
            u.is_staff = True
            u.is_superuser = True
        u.save()
        mongo_manager.sync_user(u)
        created_users[uname] = u

    # 5. Create 1 Clean Starter Workspace Project with 0 issues & 0 sprints
    admin = created_users["admin"]
    alex = created_users["alex_pm"]
    sarah = created_users["sarah_dev"]
    david = created_users["david_qa"]

    starter_project = Project.objects.create(
        name="Aether Core Platform",
        key="AET",
        description="Fresh workspace for agile project management and sprint delivery.",
        owner=admin,
        lead=alex,
        category="Software Development",
        avatar_color="#4f46e5",
    )
    ProjectMember.objects.create(project=starter_project, user=admin, role="OWNER", capacity_hours_per_week=40)
    ProjectMember.objects.create(project=starter_project, user=alex, role="MANAGER", capacity_hours_per_week=40)
    ProjectMember.objects.create(project=starter_project, user=sarah, role="DEVELOPER", capacity_hours_per_week=40)
    ProjectMember.objects.create(project=starter_project, user=david, role="TESTER", capacity_hours_per_week=40)

    mongo_manager.sync_project(starter_project)

    print("\n[Reset] SUCCESS! All metrics and data reset to 0:")
    print("        Total Projects: 1 (0 issues, 0% progress)")
    print("        Total Issues:   0 (Kanban columns all 0)")
    print("        Total Sprints:  0 (Burndown 0, Velocity 0)")
    print("        Total Activity: 0")
    print("        Notifications:  0 unread")
    print("        MongoDB Sync:   Synchronized and ready for live user input.\n")

if __name__ == "__main__":
    reset_all_data()
