import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User
from projects.models import Project, ProjectMember
from mongodb_engine.manager import mongo_manager

def clean_users():
    print("[Clean] Removing dummy mock users and setting Aayush Shah as workspace owner...")

    # Find or create Aayush Shah
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
        user.role = "ADMIN"
        user.is_staff = True
        user.is_superuser = True
        user.save()

    # Reassign any projects to Aayush Shah
    for p in Project.objects.all():
        p.owner = user
        p.lead = user
        p.save()
        ProjectMember.objects.filter(project=p).exclude(user=user).delete()
        ProjectMember.objects.get_or_create(project=p, user=user, defaults={"role": "OWNER", "capacity_hours_per_week": 40})
        mongo_manager.sync_project(p)

    # Delete dummy mock users
    deleted_count, _ = User.objects.exclude(pk=user.pk).delete()
    print(f"[Clean] Deleted {deleted_count} mock users. Active user: {user.display_name} ({user.username})")

    # Sync MongoDB users collection
    if mongo_manager.is_connected and mongo_manager.db is not None:
        mongo_manager.db["users"].delete_many({})
        mongo_manager.sync_user(user)

    print("[Clean] Completed successfully! Only real user data remains.")

if __name__ == "__main__":
    clean_users()
