from django.urls import path
from .views import (
    AIChatAPI,
    AISprintPlannerAPI,
    AISprintRiskAPI,
    AIIssueImprovementAPI,
    AIIssueBreakdownAPI,
    AIAcceptanceCriteriaAPI,
    AIPrioritySuggestionAPI,
    AIStoryPointEstimationAPI,
    AIFindSimilarAPI,
    AIProjectSummaryAPI,
    AIStandupGeneratorAPI,
    AIDailyWorkAPI,
    AIApplyActionAPI,
    AIAllocateWorkAPI,
)

app_name = "ai_assistant"

urlpatterns = [
    path("chat/", AIChatAPI.as_view(), name="chat"),
    path("plan-sprint/", AISprintPlannerAPI.as_view(), name="plan_sprint"),
    path("analyze-sprint/", AISprintRiskAPI.as_view(), name="analyze_sprint"),
    path("improve-issue/", AIIssueImprovementAPI.as_view(), name="improve_issue"),
    path("breakdown-issue/", AIIssueBreakdownAPI.as_view(), name="breakdown_issue"),
    path("acceptance-criteria/", AIAcceptanceCriteriaAPI.as_view(), name="acceptance_criteria"),
    path("suggest-priority/", AIPrioritySuggestionAPI.as_view(), name="suggest_priority"),
    path("estimate-points/", AIStoryPointEstimationAPI.as_view(), name="estimate_points"),
    path("find-similar/", AIFindSimilarAPI.as_view(), name="find_similar"),
    path("project-summary/", AIProjectSummaryAPI.as_view(), name="project_summary"),
    path("standup/", AIStandupGeneratorAPI.as_view(), name="standup"),
    path("my-work-recommendations/", AIDailyWorkAPI.as_view(), name="daily_work"),
    path("allocate-work/", AIAllocateWorkAPI.as_view(), name="allocate_work"),
    path("apply-action/", AIApplyActionAPI.as_view(), name="apply_action"),
]
