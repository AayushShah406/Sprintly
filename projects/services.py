from .models import Project

def archive_project(*,project,user):
    if project.owner!=user:
        raise PermissionError("Only the project owner can archive this project")

    project.is_archived=True
    project.save(update_fields=["is_archived","updated_at"])

    return project