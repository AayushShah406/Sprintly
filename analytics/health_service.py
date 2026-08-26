import json
import math
from datetime import date, datetime, timedelta, timezone
from sprints.models import Sprint
from issues.models import Issue
from analytics.models import SprintHealthSnapshot
from events_engine.broker import event_broker
from mongodb_engine.manager import mongo_manager
from config.crypto_utils import compute_sha256_hash

class SprintHealthEngine:
    """
    State-of-the-art Sprint Health & Risk Assessment Engine.
    Computes real-time health scores across 5 core dimensions with predictive diagnostics.
    """

    @classmethod
    def evaluate_sprint(cls, sprint: Sprint) -> dict:
        issues = list(sprint.issues.all().select_related("assignee"))
        total_issues = len(issues)
        
        if total_issues == 0:
            return {
                "sprint_id": sprint.pk,
                "sprint_name": sprint.name,
                "health_score": 100,
                "status_label": "HEALTHY",
                "status_color": "#10b981",
                "burndown_score": 100,
                "scope_creep_score": 100,
                "bottleneck_score": 100,
                "workload_score": 100,
                "completion_probability": 100,
                "total_points": 0,
                "completed_points": 0,
                "remaining_points": 0,
                "days_remaining": 0,
                "diagnostics": [
                    {
                        "severity": "INFO",
                        "category": "Backlog",
                        "title": "Empty Sprint",
                        "message": "Add user stories or tasks to this sprint to begin tracking velocity."
                    }
                ],
                "burndown_data": {
                    "labels": ["Day 1", "Day 5", "Day 10"],
                    "ideal": [0, 0, 0],
                    "actual": [0, 0, 0],
                }
            }

        total_points = sum(i.story_points for i in issues)
        done_issues = [i for i in issues if i.status == "DONE"]
        in_progress_issues = [i for i in issues if i.status == "IN_PROGRESS"]
        in_review_issues = [i for i in issues if i.status == "IN_REVIEW"]
        todo_issues = [i for i in issues if i.status in ["TODO", "BACKLOG"]]
        critical_issues = [i for i in issues if i.priority == "CRITICAL" and i.status != "DONE"]
        unassigned_issues = [i for i in issues if i.assignee is None and i.status != "DONE"]

        completed_points = sum(i.story_points for i in done_issues)
        in_progress_points = sum(i.story_points for i in in_progress_issues)
        remaining_points = max(0, total_points - completed_points)

        # 1. Timeline & Burndown Analysis
        today = date.today()
        start = sprint.start_date or (today - timedelta(days=5))
        end = sprint.end_date or (today + timedelta(days=9))
        
        total_duration_days = max(1, (end - start).days)
        elapsed_days = max(0, (today - start).days)
        time_elapsed_ratio = min(1.0, elapsed_days / total_duration_days)
        points_done_ratio = completed_points / max(1, total_points)

        # Burndown Score calculation (100 is ideal, penalize lag)
        velocity_deficit = max(0.0, time_elapsed_ratio - points_done_ratio)
        burndown_score = max(20, int(100 - (velocity_deficit * 120)))

        # 2. Scope Creep Index
        # Compare committed points vs current total points
        committed = sprint.total_committed_points if sprint.total_committed_points > 0 else total_points
        if total_points > committed:
            creep_pct = ((total_points - committed) / committed) * 100
            scope_creep_score = max(20, int(100 - (creep_pct * 2.0)))
        else:
            scope_creep_score = 100

        # 3. Blocker & Bottleneck Index
        bottleneck_penalty = 0
        if len(critical_issues) > 0:
            bottleneck_penalty += len(critical_issues) * 15
        if len(in_review_issues) > 3:
            bottleneck_penalty += (len(in_review_issues) - 3) * 8
        if len(unassigned_issues) > 0:
            bottleneck_penalty += len(unassigned_issues) * 10
        bottleneck_score = max(15, 100 - bottleneck_penalty)

        # 4. Workload Imbalance Index
        assignee_points = {}
        for issue in issues:
            user_name = issue.assignee.username if issue.assignee else "Unassigned"
            assignee_points[user_name] = assignee_points.get(user_name, 0) + issue.story_points
        
        counts = list(assignee_points.values())
        if len(counts) > 1:
            avg_pts = sum(counts) / len(counts)
            variance = sum((x - avg_pts) ** 2 for x in counts) / len(counts)
            std_dev = math.sqrt(variance)
            workload_penalty = min(60, int(std_dev * 5))
            workload_score = max(30, 100 - workload_penalty)
        else:
            workload_score = 90

        # 5. Completion Probability Forecast (%)
        days_left = max(0, (end - today).days)
        if time_elapsed_ratio > 0.1:
            burn_rate_per_day = completed_points / max(1, elapsed_days)
            projected_completion = completed_points + (burn_rate_per_day * days_left)
            completion_probability = min(99, max(10, int((projected_completion / max(1, total_points)) * 100)))
        else:
            completion_probability = 95

        # Composite Health Score (Weighted)
        composite = int(
            (burndown_score * 0.35) +
            (scope_creep_score * 0.20) +
            (bottleneck_score * 0.25) +
            (workload_score * 0.20)
        )
        health_score = max(10, min(100, composite))

        if health_score >= 80:
            status_label = "HEALTHY"
            status_color = "#10b981"
        elif health_score >= 55:
            status_label = "MODERATE_RISK"
            status_color = "#f59e0b"
        else:
            status_label = "CRITICAL_RISK"
            status_color = "#ef4444"

        # Actionable AI/Engine Diagnostics
        diagnostics = []
        if len(critical_issues) > 0:
            diagnostics.append({
                "severity": "CRITICAL",
                "category": "Blockers",
                "title": f"{len(critical_issues)} Critical Blocker(s) Open",
                "message": f"Blockers like {critical_issues[0].key} require immediate swarming by the team.",
                "action": f"Prioritize resolving {critical_issues[0].key}"
            })
        
        if velocity_deficit > 0.25:
            diagnostics.append({
                "severity": "WARNING",
                "category": "Velocity",
                "title": "Burndown Velocity Lag",
                "message": f"Sprint is {int(velocity_deficit * 100)}% behind projected burndown schedule.",
                "action": "Consider deselecting non-essential tasks or splitting large stories."
            })
        
        if len(in_review_issues) >= 3:
            diagnostics.append({
                "severity": "WARNING",
                "category": "Code Review",
                "title": "Review Bottleneck",
                "message": f"{len(in_review_issues)} tickets are waiting in QA/Review.",
                "action": "Trigger team review swarm to unblock merges."
            })
        
        if len(unassigned_issues) > 0:
            diagnostics.append({
                "severity": "WARNING",
                "category": "Ownership",
                "title": f"{len(unassigned_issues)} Unassigned Ticket(s)",
                "message": "Active sprint tasks without clear ownership cause delivery delays.",
                "action": "Assign owners in the sprint planning board."
            })
        
        # Check high workload individual
        for user_name, pts in assignee_points.items():
            if user_name != "Unassigned" and pts > (total_points * 0.5) and total_points > 10:
                diagnostics.append({
                    "severity": "INFO",
                    "category": "Workload",
                    "title": f"High Capacity Concentration on @{user_name}",
                    "message": f"@{user_name} holds {pts} of {total_points} total story points ({int(pts/total_points*100)}%).",
                    "action": "Rebalance sprint workload across other available engineers."
                })
                break

        if not diagnostics:
            diagnostics.append({
                "severity": "SUCCESS",
                "category": "Execution",
                "title": "Sprint On Track",
                "message": "Team velocity, capacity, and burndown are in optimal synchronization.",
                "action": "Maintain current deployment pace."
            })

        # Generate realistic burndown timeline
        burndown_labels = []
        ideal_burndown = []
        actual_burndown = []
        
        days_count = max(5, min(14, total_duration_days))
        pts_step = total_points / (days_count - 1) if days_count > 1 else 0
        
        current_actual = total_points
        for idx in range(days_count):
            d = start + timedelta(days=idx)
            burndown_labels.append(d.strftime("%b %d"))
            ideal_burndown.append(round(max(0, total_points - (idx * pts_step)), 1))
            
            if d <= today:
                # Interpolate actual burndown up to today
                progress_step = (total_points - remaining_points) / max(1, elapsed_days)
                val = max(remaining_points, round(total_points - (idx * progress_step), 1))
                actual_burndown.append(val)
            else:
                actual_burndown.append(None)

        result = {
            "sprint_id": sprint.pk,
            "sprint_name": sprint.name,
            "sprint_goal": sprint.goal,
            "status": sprint.status,
            "health_score": health_score,
            "status_label": status_label,
            "status_color": status_color,
            "burndown_score": burndown_score,
            "scope_creep_score": scope_creep_score,
            "bottleneck_score": bottleneck_score,
            "workload_score": workload_score,
            "completion_probability": completion_probability,
            "total_points": total_points,
            "completed_points": completed_points,
            "in_progress_points": in_progress_points,
            "remaining_points": remaining_points,
            "days_remaining": days_left,
            "total_issues": total_issues,
            "done_issues_count": len(done_issues),
            "in_progress_count": len(in_progress_issues),
            "in_review_count": len(in_review_issues),
            "todo_count": len(todo_issues),
            "diagnostics": diagnostics,
            "workload_distribution": assignee_points,
            "burndown_data": {
                "labels": burndown_labels,
                "ideal": ideal_burndown,
                "actual": actual_burndown,
            }
        }

        # Save snapshot into SQLite & MongoDB (with rate limiting)
        try:
            from django.utils import timezone as dj_timezone
            last_snapshot = SprintHealthSnapshot.objects.filter(sprint=sprint).order_by("-created_at").first()
            should_save = True
            if last_snapshot:
                delta = dj_timezone.now() - last_snapshot.created_at
                if delta.total_seconds() < 60:
                    should_save = False

            if should_save:
                SprintHealthSnapshot.objects.create(
                    sprint=sprint,
                    health_score=health_score,
                    status_label=status_label,
                    burndown_score=burndown_score,
                    scope_creep_score=scope_creep_score,
                    bottleneck_score=bottleneck_score,
                    workload_score=workload_score,
                    completion_probability=completion_probability,
                    diagnostics_json=json.dumps(diagnostics),
                )
                
                # MongoDB Document Store
                mongo_manager.insert_document("sprint_health_snapshots", {
                    "sprint_id": sprint.pk,
                    "sprint_name": sprint.name,
                    "health_score": health_score,
                    "status_label": status_label,
                    "metrics": {
                        "burndown": burndown_score,
                        "scope_creep": scope_creep_score,
                        "bottlenecks": bottleneck_score,
                        "workload": workload_score,
                        "prob": completion_probability,
                    },
                    "diagnostics": diagnostics,
                    "evaluated_at": datetime.now(timezone.utc).isoformat(),
                })

                # Publish event to Event Broker
                event_broker.publish(
                    topic="sprintly.sprints.health",
                    event_type="HEALTH_EVALUATED",
                    payload={"sprint_id": sprint.pk, "score": health_score, "status": status_label},
                    actor="SprintHealthEngine"
                )
        except Exception as e:
            pass

        return result
