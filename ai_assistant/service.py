import os
import json
import logging
from datetime import date, timedelta
from typing import Dict, Any, List, Optional
from django.conf import settings
from django.db.models import Q, Count, Sum
from projects.models import Project, ProjectMember
from sprints.models import Sprint
from issues.models import Issue, SubTask, Comment, IssueAuditLog
from accounts.models import User

logger = logging.getLogger(__name__)

# Preferred models in order of priority on Groq
GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "groq/compound",
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
]

class SprintlyAIEngine:
    """
    Sprintly AI Engine powered by Groq LLM with full real-time database snapshot integration.
    Provides direct decision support for Sprint Planning, Risk Analysis, Issue Improvement,
    Standup Generation, and Interactive Project Q&A.
    """

    def _get_client(self):
        """Dynamically retrieves or creates the Groq client using the active GROQ_API_KEY in environment."""
        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not api_key:
            return None
        try:
            from groq import Groq
            return Groq(api_key=api_key)
        except Exception as e:
            logger.error(f"[SprintlyAI] Failed to initialize Groq client: {e}")
            return None

    def _call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: int = 1500) -> Optional[str]:
        """Invokes Groq LLM with automatic model failover across supported model IDs."""
        client = self._get_client()
        if not client:
            return None

        configured_model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
        models_to_try = [configured_model] + [m for m in GROQ_MODELS if m != configured_model]

        for model_id in models_to_try:
            try:
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    model=model_id,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = chat_completion.choices[0].message.content
                if content:
                    return content.strip()
            except Exception as e:
                logger.warning(f"[SprintlyAI] Model {model_id} failed: {e}. Trying next model...")

        return None

    # =========================================================================
    # 1. AI SPRINT PLANNER
    # =========================================================================
    def plan_sprint(self, project: Project, user: User, target_capacity: Optional[int] = None) -> Dict[str, Any]:
        """
        Analyzes backlog issues, team velocity, and capacity to recommend an optimal sprint scope.
        """
        backlog_issues = list(project.issues.filter(sprint__isnull=True).exclude(status="DONE").order_by("-priority", "-created_at"))
        members = project.memberships.select_related("user").all()
        
        calculated_capacity = sum(m.capacity_hours_per_week for m in members) // 2
        capacity = target_capacity or max(10, calculated_capacity or 20)

        items_summary = [
            {"key": i.key, "id": i.pk, "title": i.title, "type": i.issue_type, "priority": i.priority, "points": i.story_points}
            for i in backlog_issues
        ]

        if items_summary:
            system_prompt = (
                "You are Sprintly AI, an expert Agile Scrum Coach and Sprint Planning Specialist. "
                "Recommend which backlog issues should be included in the next sprint based on team capacity, "
                "story points, and priority (CRITICAL > HIGH > MEDIUM > LOW). "
                "Select strictly from the provided backlog list without inventing new IDs. "
                "Return valid JSON matching this schema:\n"
                "{\n"
                '  "recommended_issue_ids": [1, 2],\n'
                '  "total_points": 14,\n'
                '  "capacity": 18,\n'
                '  "confidence": "HIGH",\n'
                '  "reasoning": "Clear explanation of prioritization and capacity fit."\n'
                "}"
            )
            user_prompt = f"Project: {project.key} ({project.name})\nTarget Capacity: {capacity} story points\nBacklog Issues:\n{json.dumps(items_summary)}"

            response_text = self._call_llm(system_prompt, user_prompt, temperature=0.1)
            if response_text:
                try:
                    clean_json = response_text.replace("```json", "").replace("```", "").strip()
                    result = json.loads(clean_json)
                    rec_ids = result.get("recommended_issue_ids", [])
                    rec_issues = [
                        {"id": i.pk, "key": i.key, "title": i.title, "priority": i.priority, "points": i.story_points, "type": i.issue_type}
                        for i in backlog_issues if i.pk in rec_ids
                    ]
                    if rec_issues:
                        return {
                            "success": True,
                            "recommended_issues": rec_issues,
                            "total_points": sum(i["points"] for i in rec_issues),
                            "capacity": capacity,
                            "confidence": result.get("confidence", "HIGH"),
                            "reasoning": result.get("reasoning", "Optimized scope based on team capacity and issue priority."),
                        }
                except Exception as e:
                    logger.error(f"[SprintlyAI] Sprint plan parse error: {e}")

        # Deterministic Domain Fallback
        accumulated_pts = 0
        selected = []
        for i in backlog_issues:
            if accumulated_pts + i.story_points <= capacity:
                selected.append({"id": i.pk, "key": i.key, "title": i.title, "priority": i.priority, "points": i.story_points, "type": i.issue_type})
                accumulated_pts += i.story_points

        return {
            "success": True,
            "recommended_issues": selected,
            "total_points": accumulated_pts,
            "capacity": capacity,
            "confidence": "HIGH" if accumulated_pts > 0 else "MEDIUM",
            "reasoning": (
                f"Selected {len(selected)} backlog issues prioritizing High/Critical tickets "
                f"to match your estimated team capacity of {capacity} story points."
                if selected else "The backlog is currently empty. Add issues to your project backlog or click '+ Create Issue' to start planning your sprint."
            ),
        }

    # =========================================================================
    # 2. AI SPRINT RISK ANALYSIS
    # =========================================================================
    def analyze_sprint_risk(self, sprint: Sprint, user: User) -> Dict[str, Any]:
        """
        Analyzes active sprint health, bottlenecks, remaining velocity, and predicts delivery risks.
        """
        issues = list(sprint.issues.select_related("assignee").all())
        total_pts = sum(i.story_points for i in issues)
        done_pts = sum(i.story_points for i in issues if i.status == "DONE")
        remaining_pts = max(0, total_pts - done_pts)
        
        blocked_issues = [i for i in issues if i.status == "BLOCKED"]
        overdue_issues = [i for i in issues if i.is_overdue and i.status != "DONE"]
        unassigned_issues = [i for i in issues if not i.assignee and i.status != "DONE"]

        days_remaining = 0
        if sprint.end_date:
            days_remaining = max(0, (sprint.end_date - date.today()).days)

        risks = []
        if len(blocked_issues) > 0:
            risks.append(f"⚠ {len(blocked_issues)} issue(s) are currently marked as BLOCKED.")
        if days_remaining <= 3 and remaining_pts > 10:
            risks.append(f"⚠ {remaining_pts} story points remain with only {days_remaining} day(s) left.")
        if len(unassigned_issues) > 0:
            risks.append(f"⚠ {len(unassigned_issues)} active sprint issue(s) are unassigned.")
        if len(overdue_issues) > 0:
            risks.append(f"⚠ {len(overdue_issues)} issue(s) have passed their target due date.")

        health_score = 95
        health_score -= (len(blocked_issues) * 12)
        health_score -= (len(overdue_issues) * 10)
        health_score -= (len(unassigned_issues) * 5)
        if days_remaining > 0 and (remaining_pts / max(1, days_remaining)) > 8:
            health_score -= 15
        health_score = max(20, min(100, health_score))

        risk_level = "LOW"
        if health_score < 50:
            risk_level = "CRITICAL"
        elif health_score < 75:
            risk_level = "HIGH"
        elif health_score < 88:
            risk_level = "MEDIUM"

        system_prompt = (
            "You are Sprintly AI, an executive Agile Risk Consultant. "
            "Analyze the sprint metrics and provide 3-4 specific, actionable recommendations for the engineering team. "
            "Return valid JSON:\n"
            "{\n"
            '  "recommendations": ["Recommendation 1", "Recommendation 2"]\n'
            "}"
        )

        user_prompt = (
            f"Sprint: {sprint.name} (Goal: {sprint.goal})\n"
            f"Total Points: {total_pts}, Done: {done_pts}, Remaining: {remaining_pts}\n"
            f"Days Left: {days_remaining}\n"
            f"Blocked Issues: {[i.key + ': ' + i.title for i in blocked_issues]}\n"
            f"Overdue Issues: {[i.key for i in overdue_issues]}\n"
            f"Unassigned: {[i.key for i in unassigned_issues]}"
        )

        recs = []
        response_text = self._call_llm(system_prompt, user_prompt, temperature=0.2)
        if response_text:
            try:
                clean_json = response_text.replace("```json", "").replace("```", "").strip()
                recs = json.loads(clean_json).get("recommendations", [])
            except Exception:
                pass

        if not recs:
            if blocked_issues:
                recs.append(f"Resolve blocker on {blocked_issues[0].key} before starting downstream tasks.")
            if days_remaining <= 3 and remaining_pts > 8:
                recs.append("Consider rolling over lower priority tasks to the next sprint.")
            if unassigned_issues:
                recs.append(f"Assign {unassigned_issues[0].key} to an available team engineer.")
            if not recs:
                recs.append("Sprint velocity is tracking well within planned capacity limits.")

        return {
            "success": True,
            "sprint_name": sprint.name,
            "health_score": health_score,
            "risk_level": risk_level,
            "detected_risks": risks or ["No critical risk factors detected. Sprint is on schedule."],
            "recommendations": recs,
            "remaining_points": remaining_pts,
            "days_remaining": days_remaining,
        }

    # =========================================================================
    # 3. AI ISSUE ASSISTANT (Improve with AI)
    # =========================================================================
    def improve_issue(self, raw_title: str, raw_description: str, user: User) -> Dict[str, Any]:
        """
        Analyzes draft title/description and returns professional SaaS-grade refinement.
        """
        system_prompt = (
            "You are Sprintly AI Issue Assistant. Transform informal, vague software ticket drafts into clear, "
            "actionable user stories or bug tickets with high technical clarity.\n"
            "Return valid JSON matching this schema:\n"
            "{\n"
            '  "title": "Improved concise professional title",\n'
            '  "description": "Structured description with context and expected behavior",\n'
            '  "issue_type": "STORY" | "TASK" | "BUG" | "IMPROVEMENT",\n'
            '  "priority": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",\n'
            '  "story_points": 3,\n'
            '  "labels": "frontend, auth, ui",\n'
            '  "acceptance_criteria": ["Criterion 1", "Criterion 2", "Criterion 3"],\n'
            '  "suggested_subtasks": ["Subtask 1", "Subtask 2"]\n'
            "}"
        )

        user_prompt = f"Draft Title: {raw_title}\nDraft Description: {raw_description}"

        response_text = self._call_llm(system_prompt, user_prompt, temperature=0.2)
        if response_text:
            try:
                clean_json = response_text.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
                return {"success": True, "suggestion": data}
            except Exception as e:
                logger.error(f"[SprintlyAI] Issue improvement parse error: {e}")

        # Deterministic Rule-Based Fallback
        is_bug = any(w in raw_title.lower() or w in raw_description.lower() for w in ["bug", "error", "fail", "broken", "crash", "fix", "doesn't work"])
        improved_title = raw_title.strip()
        if not improved_title.endswith((".", "!", "?")):
            improved_title = f"Implement {improved_title}" if not is_bug else f"Fix: {improved_title}"

        return {
            "success": True,
            "suggestion": {
                "title": improved_title,
                "description": f"{raw_description.strip()}\n\n### Acceptance Criteria & Verification\nEnsure reliable performance, clean error boundaries, and unit test coverage.",
                "issue_type": "BUG" if is_bug else "STORY",
                "priority": "HIGH" if is_bug else "MEDIUM",
                "story_points": 5 if is_bug else 3,
                "labels": "bug, core" if is_bug else "feature, enhancement",
                "acceptance_criteria": [
                    "Feature performs reliably under expected load.",
                    "Input validation and error states are clearly displayed.",
                    "Responsive layout is verified across viewport sizes."
                ],
                "suggested_subtasks": [
                    "Implement core business logic and state updates",
                    "Add automated unit and regression tests",
                    "Perform peer code review and validation"
                ]
            }
        }

    # =========================================================================
    # 4. AI ISSUE BREAKDOWN & ACCEPTANCE CRITERIA
    # =========================================================================
    def breakdown_issue(self, issue: Issue, user: User) -> List[str]:
        """Breaks down a large issue into smaller atomic subtasks."""
        system_prompt = (
            "You are Sprintly AI. Break down the provided software issue into 4-6 atomic, actionable technical subtasks. "
            "Return valid JSON: {\"subtasks\": [\"Subtask 1\", \"Subtask 2\"]}"
        )
        user_prompt = f"Issue: {issue.key} - {issue.title}\nDescription: {issue.description}\nType: {issue.issue_type}"

        response_text = self._call_llm(system_prompt, user_prompt)
        if response_text:
            try:
                clean_json = response_text.replace("```json", "").replace("```", "").strip()
                return json.loads(clean_json).get("subtasks", [])
            except Exception:
                pass

        return [
            f"Define specifications and data contracts for {issue.title}",
            "Implement backend logic and endpoints",
            "Build UI component and bind state handlers",
            "Write unit tests and perform QA verification"
        ]

    def generate_acceptance_criteria(self, issue: Issue, user: User) -> List[str]:
        """Generates clear, testable acceptance criteria for an issue."""
        system_prompt = (
            "You are Sprintly AI. Generate 4-6 testable, unambiguous acceptance criteria in Given-When-Then or clear checklist format. "
            "Return valid JSON: {\"criteria\": [\"Criterion 1\", \"Criterion 2\"]}"
        )
        user_prompt = f"Issue: {issue.key} - {issue.title}\nDescription: {issue.description}"

        response_text = self._call_llm(system_prompt, user_prompt)
        if response_text:
            try:
                clean_json = response_text.replace("```json", "").replace("```", "").strip()
                return json.loads(clean_json).get("criteria", [])
            except Exception:
                pass

        return [
            f"User can successfully execute {issue.title} workflow.",
            "Appropriate validation errors are displayed for invalid inputs.",
            "System state is securely persisted to the database.",
            "Performance and response time meet standard SLA guidelines."
        ]

    # =========================================================================
    # 5. AI PRIORITY & STORY POINT ESTIMATION
    # =========================================================================
    def suggest_priority(self, issue: Issue, user: User) -> Dict[str, Any]:
        """Analyzes impact, type, and blockers to suggest priority."""
        has_blockers = issue.outgoing_links.filter(link_type="BLOCKS").exists()
        is_bug = issue.issue_type == "BUG"
        
        suggested = "HIGH" if (has_blockers or is_bug) else "MEDIUM"
        reason = "Issue blocks other tickets in the workspace." if has_blockers else "Standard feature work with medium business impact."
        
        return {
            "current_priority": issue.priority,
            "suggested_priority": suggested,
            "reason": reason
        }

    def estimate_story_points(self, issue: Issue, user: User) -> Dict[str, Any]:
        """Estimates story points (1, 2, 3, 5, 8, 13) with confidence rating."""
        desc_len = len(issue.description or "")
        points = 5 if desc_len > 200 else (3 if desc_len > 50 else 2)
        if issue.issue_type == "EPIC":
            points = 13

        return {
            "suggested_points": points,
            "confidence": "HIGH" if desc_len > 100 else "MEDIUM",
            "reason": "Estimate based on complexity, backend dependencies, and testing requirements."
        }

    # =========================================================================
    # 6. AI DUPLICATE / SIMILAR ISSUE DETECTION
    # =========================================================================
    def find_similar_issues(self, title: str, project: Project, user: User, exclude_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Finds potential duplicate issues within the user's project."""
        words = [w.lower() for w in title.split() if len(w) > 3]
        if not words:
            return []

        q = Q()
        for w in words:
            q |= Q(title__icontains=w) | Q(description__icontains=w)

        qs = project.issues.filter(q)
        if exclude_id:
            qs = qs.exclude(pk=exclude_id)

        results = []
        for i in qs[:4]:
            match_score = 85 if words[0] in i.title.lower() else 70
            results.append({
                "id": i.pk,
                "key": i.key,
                "title": i.title,
                "status": i.status,
                "similarity_pct": match_score
            })
        return sorted(results, key=lambda x: x["similarity_pct"], reverse=True)

    # =========================================================================
    # 7. AI PROJECT SUMMARY & RISK DETECTION
    # =========================================================================
    def summarize_project(self, project: Project, user: User) -> Dict[str, Any]:
        """Generates comprehensive executive project summary."""
        total = project.issues.count()
        done = project.issues.filter(status="DONE").count()
        progress = project.progress_percentage
        active_sprint = project.sprints.filter(status="ACTIVE").first()
        blocked = project.issues.filter(status="BLOCKED").count()

        summary_text = (
            f"Project **{project.name}** ({project.key}) is currently **{progress}% complete** with **{done}/{total} issues** delivered. "
            f"{'Active sprint: ' + active_sprint.name + '.' if active_sprint else 'No sprint currently active.'} "
            f"{str(blocked) + ' issue(s) are currently marked as blocked.' if blocked > 0 else 'All active work is unblocked.'}"
        )

        return {
            "success": True,
            "project_name": project.name,
            "progress": progress,
            "summary": summary_text,
            "metrics": {
                "total_issues": total,
                "done_issues": done,
                "blocked_issues": blocked,
                "active_sprint": active_sprint.name if active_sprint else "None"
            }
        }

    # =========================================================================
    # 8. AI STANDUP & DAILY WORK RECOMMENDATIONS
    # =========================================================================
    def generate_standup(self, user: User) -> Dict[str, Any]:
        """Compiles personal standup based on the user's active/completed tickets."""
        completed = list(Issue.objects.filter(assignee=user, status="DONE").order_by("-updated_at")[:3])
        in_flight = list(Issue.objects.filter(assignee=user, status__in=["IN_PROGRESS", "IN_REVIEW"]).order_by("-priority")[:3])
        blocked = list(Issue.objects.filter(assignee=user, status="BLOCKED")[:2])

        yesterday = [f"Delivered {i.key}: {i.title}" for i in completed] or ["Completed assigned code reviews and backlog refinement"]
        today = [f"Work on {i.key}: {i.title}" for i in in_flight] or ["Pick up next prioritized task from active sprint"]
        blockers = [f"{i.key} is currently blocked" for i in blocked] or ["No blockers at this time"]

        return {
            "success": True,
            "yesterday": yesterday,
            "today": today,
            "blockers": blockers
        }

    def recommend_daily_work(self, user: User) -> List[Dict[str, Any]]:
        """Recommends prioritized order of daily work for the user."""
        my_issues = list(Issue.objects.filter(assignee=user).exclude(status="DONE").order_by("-priority", "due_date")[:5])
        
        recommendations = []
        for idx, i in enumerate(my_issues, start=1):
            reason = "High priority ticket in active sprint" if i.priority in ["CRITICAL", "HIGH"] else "Next scheduled task"
            if i.is_overdue:
                reason = "Past due date — requires immediate resolution"
            elif i.due_date and (i.due_date - date.today()).days <= 2:
                reason = "Target due date approaching"

            recommendations.append({
                "rank": idx,
                "id": i.pk,
                "key": i.key,
                "title": i.title,
                "priority": i.priority,
                "reason": reason
            })
        return recommendations

    # =========================================================================
    # 9. NATURAL LANGUAGE CONVERSATIONAL ASSISTANT (LIVE SNAPSHOT)
    # =========================================================================
    def ask_natural_language(self, query: str, context_data: Dict[str, Any], user: User) -> Dict[str, Any]:
        """
        Answers natural language questions with real-time live database snapshot telemetry.
        """
        # 1. Compile Live Workspace Snapshot
        all_projects = list(Project.objects.filter(is_archived=False).order_by("-created_at"))
        all_issues = Issue.objects.all()
        active_sprints = list(Sprint.objects.filter(status="ACTIVE"))
        team_members = list(User.objects.filter(is_active=True))

        active_projects = [p for p in all_projects if p.status == "ACTIVE"]
        pending_projects = [p for p in all_projects if p.status != "ACTIVE"]

        projects_summary = [
            {
                "id": p.id,
                "key": p.key,
                "name": p.name,
                "status": p.status,
                "issues_count": p.issues.count(),
                "progress": f"{p.progress_percentage}%"
            }
            for p in all_projects
        ]

        live_workspace_snapshot = {
            "current_user": {
                "username": user.username if user else "Anonymous",
                "display_name": user.display_name if user else "Engineer",
                "role": user.role if user else "DEVELOPER"
            },
            "workspace_metrics": {
                "total_projects_count": len(all_projects),
                "active_projects_count": len(active_projects),
                "pending_or_archived_projects_count": len(pending_projects),
                "projects_list": projects_summary,
                "total_issues_count": all_issues.count(),
                "open_issues_count": all_issues.exclude(status="DONE").count(),
                "completed_issues_count": all_issues.filter(status="DONE").count(),
                "blocked_issues_count": all_issues.filter(status="BLOCKED").count(),
                "active_sprints_count": len(active_sprints),
                "active_sprints_list": [{"name": s.name, "project": s.project.name, "goal": s.goal} for s in active_sprints],
                "team_members_count": len(team_members),
                "team_members_list": [u.display_name for u in team_members],
            },
            "page_context": context_data.get("type", "WORKSPACE"),
        }

        system_prompt = (
            "You are Sprintly AI, the deeply integrated intelligence system for the Sprintly enterprise platform.\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. You have direct live read access to the user's workspace database. The live database snapshot is provided in the JSON context below.\n"
            "2. NEVER say 'I don't have a live view of your workspace' or 'I cannot see your data' or give generic tutorial steps when asked about project status.\n"
            "3. Answer DIRECTLY with the real, live counts, names, statuses, and tickets from the provided workspace snapshot.\n"
            "4. If the user asks about pending/active projects and there are 0, say: 'You currently have **0 pending projects** (and **0 active projects**) in your workspace. You can create your first workspace by clicking the **+ New Project** button on the Projects page.'\n"
            "5. If there are projects/issues, cite their exact keys, exact names, story points, and exact progress percentages.\n"
            "6. If the user asks general software engineering, agile theory, architecture, or planning questions, provide rich, expert, actionable advice.\n"
            "7. Always be direct, concise, and helpful. Use clean Markdown formatting."
        )

        user_prompt = f"Live Workspace Snapshot:\n{json.dumps(live_workspace_snapshot, default=str)}\n\nUser Question:\n{query}"

        response_text = self._call_llm(system_prompt, user_prompt, temperature=0.2, max_tokens=1500)
        
        # Fallback if LLM is unavailable
        if not response_text:
            if "project" in query.lower() and ("pending" in query.lower() or "how many" in query.lower()):
                response_text = f"You currently have **{len(pending_projects)} pending project(s)** and **{len(active_projects)} active project(s)** in your workspace."
            elif "risk" in query.lower():
                response_text = f"There are currently **{all_issues.filter(status='BLOCKED').count()} blocked issue(s)** in your workspace."
            elif "work" in query.lower() or "today" in query.lower():
                response_text = f"You have **{Issue.objects.filter(assignee=user).exclude(status='DONE').count()} open ticket(s)** assigned to you in My Work."
            else:
                response_text = f"Sprintly AI is actively tracking your workspace (**{len(all_projects)} project(s)**, **{all_issues.count()} issue(s)**). How can I assist you today?"

    # =========================================================================
    # 10. AI SMART WORK ALLOCATION ENGINE
    # =========================================================================
    def allocate_team_work(self, project: Project, user: User, target_issues=None) -> Dict[str, Any]:
        """
        Analyzes team members' roles, capacity, and current active tickets to intelligently
        and evenly distribute unassigned tasks across developers, testers, designers, and leads.
        """
        memberships = list(project.memberships.select_related("user").all())
        if not memberships:
            mock_pm = type("MockPM", (), {"user": project.owner, "role": "OWNER", "capacity_hours_per_week": 40})()
            memberships = [mock_pm]

        all_issues = project.issues.select_related("assignee").all()
        if target_issues:
            unassigned_issues = list(target_issues)
        else:
            unassigned_issues = list(all_issues.filter(assignee__isnull=True, status__in=["BACKLOG", "TODO", "IN_PROGRESS"]))
            if not unassigned_issues:
                unassigned_issues = list(all_issues.filter(status__in=["BACKLOG", "TODO"]))[:8]

        member_stats = []
        for m in memberships:
            current_issues = all_issues.filter(assignee=m.user, status__in=["TODO", "IN_PROGRESS"])
            current_pts = sum(i.story_points for i in current_issues)
            cap = getattr(m, "capacity_hours_per_week", 40)
            member_stats.append({
                "user": m.user,
                "user_id": m.user.id,
                "name": m.user.display_name,
                "role": m.role if hasattr(m, "role") else getattr(m.user, "role", "DEVELOPER"),
                "title": getattr(m.user, "title", "Software Engineer"),
                "capacity": cap,
                "current_points": current_pts,
                "assigned_count": current_issues.count(),
                "avatar_color": getattr(m.user, "avatar_color", "#4f46e5"),
            })

        allocations = []
        for issue in unassigned_issues:
            candidates = sorted(member_stats, key=lambda x: (x["current_points"], x["assigned_count"]))
            best_candidate = candidates[0]

            if issue.issue_type == "BUG":
                tester_cand = [c for c in candidates if "TEST" in c["role"] or "QA" in c["title"].upper()]
                if tester_cand:
                    best_candidate = tester_cand[0]

            allocations.append({
                "issue_id": issue.id,
                "issue_key": issue.key,
                "issue_title": issue.title,
                "issue_type": issue.issue_type,
                "story_points": issue.story_points,
                "priority": issue.priority,
                "assigned_to": {
                    "id": best_candidate["user"].id,
                    "name": best_candidate["name"],
                    "role": best_candidate["role"],
                    "title": best_candidate["title"],
                    "avatar_color": best_candidate["avatar_color"],
                },
                "reasoning": f"Assigned to {best_candidate['name']} ({best_candidate['title']}) — optimal workload balancing ({best_candidate['current_points'] + issue.story_points} pts)."
            })

            best_candidate["current_points"] += issue.story_points
            best_candidate["assigned_count"] += 1

        return {
            "success": True,
            "total_allocated_issues": len(allocations),
            "allocations": allocations,
            "team_summary": [
                {
                    "name": m["name"],
                    "role": m["role"],
                    "total_points": m["current_points"],
                    "assigned_issues": m["assigned_count"]
                }
                for m in member_stats
            ]
        }


# Global Singleton instance
sprintly_ai = SprintlyAIEngine()
