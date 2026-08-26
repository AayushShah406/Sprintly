import os
import django
from datetime import date, datetime, timedelta, timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User
from projects.models import Project, ProjectMember
from sprints.models import Sprint
from issues.models import Issue, SubTask, Comment, IssueAttachment, IssueLink, IssueAuditLog
from notifications.models import Notification, TeamRoom, ChatMessage
from analytics.health_service import SprintHealthEngine
from mongodb_engine.manager import mongo_manager

def seed_database():
    print("[Seed] Initializing enterprise Sprintly database & MongoDB document sync...")

    # 1. Users with Enterprise Roles
    admin, _ = User.objects.get_or_create(
        email="admin@sprintly.io",
        defaults={
            "username": "admin",
            "first_name": "Antigravity",
            "last_name": "Admin",
            "role": "ADMIN",
            "title": "Principal System Administrator",
            "avatar_color": "#4f46e5",
            "theme_preference": "light",
        }
    )
    admin.set_password("password123")
    admin.is_staff = True
    admin.is_superuser = True
    admin.save()
    mongo_manager.sync_user(admin)

    alex, _ = User.objects.get_or_create(
        email="alex@sprintly.io",
        defaults={
            "username": "alex_pm",
            "first_name": "Alex",
            "last_name": "Mercer",
            "role": "MANAGER",
            "title": "Senior Project Manager / Scrum Master",
            "avatar_color": "#7c3aed",
            "theme_preference": "light",
        }
    )
    alex.set_password("password123")
    alex.save()
    mongo_manager.sync_user(alex)

    sarah, _ = User.objects.get_or_create(
        email="sarah@sprintly.io",
        defaults={
            "username": "sarah_dev",
            "first_name": "Sarah",
            "last_name": "Chen",
            "role": "DEVELOPER",
            "title": "Staff Backend Engineer",
            "avatar_color": "#0284c7",
            "theme_preference": "light",
        }
    )
    sarah.set_password("password123")
    sarah.save()
    mongo_manager.sync_user(sarah)

    elena, _ = User.objects.get_or_create(
        email="elena@sprintly.io",
        defaults={
            "username": "elena_dev",
            "first_name": "Elena",
            "last_name": "Rostova",
            "role": "DEVELOPER",
            "title": "Senior Frontend Engineer",
            "avatar_color": "#db2777",
            "theme_preference": "light",
        }
    )
    elena.set_password("password123")
    elena.save()
    mongo_manager.sync_user(elena)

    david, _ = User.objects.get_or_create(
        email="david@sprintly.io",
        defaults={
            "username": "david_qa",
            "first_name": "David",
            "last_name": "Kim",
            "role": "TESTER",
            "title": "Lead QA Automation Engineer",
            "avatar_color": "#059669",
            "theme_preference": "light",
        }
    )
    david.set_password("password123")
    david.save()
    mongo_manager.sync_user(david)

    # 2. Projects
    today = date.today()
    p1, _ = Project.objects.get_or_create(
        key="AET",
        defaults={
            "name": "Aether Core Platform",
            "description": "Next-generation distributed workflow and agile project delivery platform.",
            "owner": admin,
            "lead": alex,
            "category": "Cloud & Enterprise Software",
            "avatar_color": "#4f46e5",
            "start_date": today - timedelta(days=45),
            "target_date": today + timedelta(days=90),
        }
    )
    mongo_manager.sync_project(p1)

    p2, _ = Project.objects.get_or_create(
        key="SPT",
        defaults={
            "name": "Sprintly Mobile Experience",
            "description": "Native iOS & Android agile collaboration mobile application.",
            "owner": admin,
            "lead": elena,
            "category": "Mobile Application",
            "avatar_color": "#0284c7",
            "start_date": today - timedelta(days=20),
            "target_date": today + timedelta(days=120),
        }
    )
    mongo_manager.sync_project(p2)

    p3, _ = Project.objects.get_or_create(
        key="SEC",
        defaults={
            "name": "Zero-Trust Identity Gateway",
            "description": "Enterprise single sign-on, role-based access enforcement, and security auditing.",
            "owner": admin,
            "lead": sarah,
            "category": "Security & Infrastructure",
            "avatar_color": "#059669",
            "start_date": today - timedelta(days=60),
            "target_date": today + timedelta(days=30),
        }
    )
    mongo_manager.sync_project(p3)

    # Memberships
    members = [
        (admin, "OWNER", 40),
        (alex, "MANAGER", 40),
        (sarah, "DEVELOPER", 40),
        (elena, "DEVELOPER", 40),
        (david, "TESTER", 40),
    ]
    for u, r, cap in members:
        ProjectMember.objects.get_or_create(project=p1, user=u, defaults={"role": r, "capacity_hours_per_week": cap})
        ProjectMember.objects.get_or_create(project=p2, user=u, defaults={"role": r, "capacity_hours_per_week": cap})
        ProjectMember.objects.get_or_create(project=p3, user=u, defaults={"role": r, "capacity_hours_per_week": cap})

    # 3. Sprints
    sprint3, _ = Sprint.objects.get_or_create(
        project=p1,
        sprint_number=3,
        defaults={
            "name": "AET Sprint 3 (Foundations)",
            "goal": "Core data models, workspace organization, and user management.",
            "status": "COMPLETED",
            "start_date": today - timedelta(days=28),
            "end_date": today - timedelta(days=14),
            "total_committed_points": 34,
            "completed_points": 34,
        }
    )
    mongo_manager.sync_sprint(sprint3)

    sprint4, _ = Sprint.objects.get_or_create(
        project=p1,
        sprint_number=4,
        defaults={
            "name": "AET Sprint 4 (Execution & Quality)",
            "goal": "Deliver interactive Kanban board, sprint health metrics, and team collaboration hub.",
            "status": "ACTIVE",
            "start_date": today - timedelta(days=6),
            "end_date": today + timedelta(days=8),
            "total_committed_points": 42,
            "completed_points": 14,
        }
    )
    mongo_manager.sync_sprint(sprint4)

    sprint5, _ = Sprint.objects.get_or_create(
        project=p1,
        sprint_number=5,
        defaults={
            "name": "AET Sprint 5 (Scale & Reporting)",
            "goal": "Agile velocity reports, burndown tracking, and multi-project roadmaps.",
            "status": "PLANNING",
            "start_date": today + timedelta(days=9),
            "end_date": today + timedelta(days=23),
            "total_committed_points": 28,
            "completed_points": 0,
        }
    )
    mongo_manager.sync_sprint(sprint5)

    # 4. Epics
    epic1, _ = Issue.objects.get_or_create(
        project=p1,
        key="AET-100",
        defaults={
            "title": "Real-Time Collaboration & State Synchronization",
            "description": "Epic covering live board state synchronization, instant ticket updates, and activity feeds.",
            "issue_type": "EPIC",
            "priority": "HIGH",
            "status": "IN_PROGRESS",
            "story_points": 21,
            "assignee": alex,
            "reporter": admin,
            "due_date": today + timedelta(days=30),
        }
    )
    mongo_manager.sync_issue(epic1)

    epic2, _ = Issue.objects.get_or_create(
        project=p1,
        key="AET-101",
        defaults={
            "title": "Enterprise Reporting & Sprint Analytics Hub",
            "description": "Comprehensive velocity charts, burndown/burnup trajectory, and workload balance analytics.",
            "issue_type": "EPIC",
            "priority": "MEDIUM",
            "status": "TODO",
            "story_points": 13,
            "assignee": sarah,
            "reporter": admin,
            "due_date": today + timedelta(days=45),
        }
    )
    mongo_manager.sync_issue(epic2)

    # 5. Issues
    issues_list = [
        {
            "key": "AET-1",
            "title": "Design Enterprise Design System & Responsive Layout",
            "description": "Build high-contrast Light and Dark mode tokens with intuitive navigation hierarchy.",
            "issue_type": "STORY",
            "priority": "HIGH",
            "status": "DONE",
            "story_points": 5,
            "assignee": elena,
            "sprint": sprint4,
            "epic": epic1,
            "due_date": today - timedelta(days=2),
            "labels": "frontend, design, ux",
        },
        {
            "key": "AET-2",
            "title": "Implement Project & Sprint Management Endpoints",
            "description": "Robust REST API and server-rendered views for projects, sprint lifecycle, and memberships.",
            "issue_type": "TASK",
            "priority": "HIGH",
            "status": "DONE",
            "story_points": 8,
            "assignee": sarah,
            "sprint": sprint4,
            "epic": epic1,
            "due_date": today - timedelta(days=1),
            "labels": "backend, api",
        },
        {
            "key": "AET-3",
            "title": "Develop 5-Pillar Sprint Health Assessment Engine",
            "description": "Automated scoring engine evaluating burndown velocity, scope stability, bottlenecks, and capacity.",
            "issue_type": "STORY",
            "priority": "CRITICAL",
            "status": "IN_PROGRESS",
            "story_points": 8,
            "assignee": alex,
            "sprint": sprint4,
            "epic": epic2,
            "due_date": today + timedelta(days=3),
            "labels": "analytics, core-feature",
        },
        {
            "key": "AET-4",
            "title": "Interactive Drag-and-Drop Kanban Board with Instant State Save",
            "description": "Fluid HTML5 drag-and-drop movement across Backlog, To Do, In Progress, In Review, Blocked, and Done.",
            "issue_type": "STORY",
            "priority": "HIGH",
            "status": "IN_PROGRESS",
            "story_points": 5,
            "assignee": elena,
            "sprint": sprint4,
            "epic": epic1,
            "due_date": today + timedelta(days=4),
            "labels": "frontend, kanban, ui",
        },
        {
            "key": "AET-5",
            "title": "Implement Subtasks Checklist & Progress Tracker",
            "description": "Allow engineers to break complex user stories into atomic micro-tasks with live progress bar indicators.",
            "issue_type": "TASK",
            "priority": "MEDIUM",
            "status": "IN_REVIEW",
            "story_points": 5,
            "assignee": david,
            "sprint": sprint4,
            "epic": epic1,
            "due_date": today + timedelta(days=2),
            "labels": "ux, subtasks",
        },
        {
            "key": "AET-6",
            "title": "Third-Party Webhook Notification Gateway",
            "description": "External integration webhooks waiting on staging firewall rule approval.",
            "issue_type": "BUG",
            "priority": "HIGH",
            "status": "BLOCKED",
            "story_points": 5,
            "assignee": sarah,
            "sprint": sprint4,
            "epic": epic1,
            "due_date": today + timedelta(days=1),
            "labels": "integrations, blocked",
        },
        {
            "key": "AET-7",
            "title": "Team Member Capacity & Workload Allocation Matrix",
            "description": "Display developer hours commitment, assigned point distribution, and capacity warnings.",
            "issue_type": "IMPROVEMENT",
            "priority": "MEDIUM",
            "status": "TODO",
            "story_points": 3,
            "assignee": alex,
            "sprint": sprint4,
            "epic": epic2,
            "due_date": today + timedelta(days=6),
            "labels": "team, capacity",
        },
        {
            "key": "AET-8",
            "title": "Session Rate Limiting & Account Security Controls",
            "description": "Enforce sliding-window login attempts and password reset confirmation tokens.",
            "issue_type": "TASK",
            "priority": "CRITICAL",
            "status": "TODO",
            "story_points": 5,
            "assignee": david,
            "sprint": sprint4,
            "epic": None,
            "due_date": today + timedelta(days=5),
            "labels": "security, auth",
        },
        {
            "key": "AET-9",
            "title": "Roadmap Multi-Project Gantt Visualization",
            "description": "Interactive milestone timeline connecting Epics with deliverable dates.",
            "issue_type": "STORY",
            "priority": "MEDIUM",
            "status": "BACKLOG",
            "story_points": 8,
            "assignee": None,
            "sprint": None,
            "epic": epic2,
            "due_date": today + timedelta(days=25),
            "labels": "roadmap, gantt",
        },
        {
            "key": "AET-10",
            "title": "Automated Sprint Burndown & Velocity Variance Reporter",
            "description": "Generate downloadable sprint velocity summaries and completion forecasts.",
            "issue_type": "STORY",
            "priority": "LOW",
            "status": "BACKLOG",
            "story_points": 5,
            "assignee": None,
            "sprint": None,
            "epic": epic2,
            "due_date": today + timedelta(days=35),
            "labels": "reports, metrics",
        },
        {
            "key": "AET-11",
            "title": "Global Command Palette (Ctrl+K) Fuzzy Search",
            "description": "Fast unified search across projects, issues, epics, and teammates.",
            "issue_type": "IMPROVEMENT",
            "priority": "LOW",
            "status": "BACKLOG",
            "story_points": 3,
            "assignee": elena,
            "sprint": None,
            "epic": None,
            "due_date": today + timedelta(days=40),
            "labels": "search, shortcut",
        }
    ]

    for item in issues_list:
        issue, created = Issue.objects.get_or_create(
            project=p1,
            key=item["key"],
            defaults={
                "title": item["title"],
                "description": item["description"],
                "issue_type": item["issue_type"],
                "priority": item["priority"],
                "status": item["status"],
                "story_points": item["story_points"],
                "assignee": item["assignee"],
                "reporter": admin,
                "sprint": item["sprint"],
                "epic": item["epic"],
                "due_date": item["due_date"],
                "labels": item["labels"],
            }
        )
        mongo_manager.sync_issue(issue)

        if created:
            if issue.key == "AET-3":
                SubTask.objects.create(issue=issue, title="Define 5-pillar scoring algorithm weights", is_completed=True)
                SubTask.objects.create(issue=issue, title="Implement burndown deficit calculator", is_completed=True)
                SubTask.objects.create(issue=issue, title="Build AI diagnostic recommendation generator", is_completed=False)
                SubTask.objects.create(issue=issue, title="Connect live radar and circular progress gauge", is_completed=False)

                Comment.objects.create(issue=issue, author=alex, content="Sprint 4 velocity is tracking well. Let's ensure review times stay under 24 hours.")
                Comment.objects.create(issue=issue, author=sarah, content="Algorithms validated and tested against sample sprint datasets.")

                IssueAttachment.objects.create(issue=issue, file_name="sprint_health_spec.pdf", file_size="240 KB", uploaded_by=alex)
                IssueAttachment.objects.create(issue=issue, file_name="velocity_projection_v1.png", file_size="180 KB", uploaded_by=sarah)

                issue.watchers.add(admin, alex, sarah)

            log = IssueAuditLog.objects.create(
                issue=issue,
                actor=admin,
                action="Created ticket",
                new_value=f"Initial state {issue.status}"
            )
            mongo_manager.sync_audit_log(log)

    # 6. Issue Links
    aet3 = Issue.objects.filter(key="AET-3").first()
    aet4 = Issue.objects.filter(key="AET-4").first()
    aet6 = Issue.objects.filter(key="AET-6").first()
    if aet3 and aet4:
        IssueLink.objects.get_or_create(source_issue=aet3, target_issue=aet4, link_type="RELATES_TO")
    if aet6 and aet3:
        IssueLink.objects.get_or_create(source_issue=aet6, target_issue=aet3, link_type="BLOCKS")

    # 7. Notifications
    n1 = Notification.objects.create(
        recipient=admin,
        actor=alex,
        notification_type="SPRINT_STARTED",
        title="Sprint 4 has started",
        message="AET Sprint 4 (Execution & Quality) has officially commenced with 42 committed story points.",
        link="/projects/1/sprints/",
    )
    mongo_manager.sync_notification(n1)

    n2 = Notification.objects.create(
        recipient=admin,
        actor=sarah,
        notification_type="STATUS_CHANGE",
        title="AET-2 completed",
        message="Sarah Chen moved 'Implement Project & Sprint Management Endpoints' to Done.",
        link="/issues/2/",
    )
    mongo_manager.sync_notification(n2)

    n3 = Notification.objects.create(
        recipient=admin,
        actor=alex,
        notification_type="ASSIGNMENT",
        title="New Issue Assigned",
        message="You have been assigned to review AET-3 Sprint Health Assessment Engine.",
        link="/issues/3/",
    )
    mongo_manager.sync_notification(n3)

    # 8. Team Chat Rooms & Messages
    r1, _ = TeamRoom.objects.get_or_create(project=p1, name="general-dev", defaults={"description": "Main engineering discussions and announcements"})
    r2, _ = TeamRoom.objects.get_or_create(project=p1, name="sprint-planning", defaults={"description": "Backlog refinement, estimations, and sprint scope"})

    cm1 = ChatMessage.objects.create(room=r1, author=alex, content="Welcome to the Sprintly engineering hub! Sprint 4 is underway.")
    mongo_manager.insert_document("chat_messages", {"room": "general-dev", "author": alex.username, "content": cm1.content})

    cm2 = ChatMessage.objects.create(room=r1, author=sarah, content="Backend API endpoints and project services are live and tested.")
    mongo_manager.insert_document("chat_messages", {"room": "general-dev", "author": sarah.username, "content": cm2.content})

    cm3 = ChatMessage.objects.create(room=r1, author=elena, content="Kanban board drag-and-drop is ready with instant persistence.")
    mongo_manager.insert_document("chat_messages", {"room": "general-dev", "author": elena.username, "content": cm3.content})

    # Evaluate sprint 4 health so snapshot is stored in MongoDB
    SprintHealthEngine.evaluate_sprint(sprint4)

    # Queue telemetry document
    mongo_manager.insert_document("queue_telemetry", {
        "event_broker": "operational",
        "active_workers": 8,
        "processed_events": 1428,
        "average_latency_ms": 1.2,
    })

    print("[Seed] Synchronized all 9 MongoDB collections and SQLite relational database successfully!")

if __name__ == "__main__":
    seed_database()
