from projects.models import Project

def global_workspace_context(request):
    try:
        projects = list(Project.objects.filter(is_archived=False).order_by("-created_at"))
        active = projects[0] if projects else None
        return {
            "all_projects": projects,
            "project": active,
            "active_project": active,
        }
    except Exception:
        return {
            "all_projects": [],
            "project": None,
            "active_project": None,
        }
