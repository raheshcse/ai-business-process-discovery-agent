from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.project import Project
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, session: Session) -> None:
        self._repository = ProjectRepository(session)

    def create_project(self, create_data: ProjectCreate) -> Project:
        project = Project(
            name=create_data.name,
            client_name=create_data.client_name,
            department=create_data.department,
            industry=create_data.industry,
            objective=create_data.objective,
            status=create_data.status,
        )
        return self._repository.create(project)

    def list_projects(self) -> list[Project]:
        return self._repository.list()

    def get_project(self, project_id: str) -> Project | None:
        return self._repository.get(project_id)

    def update_project(self, project: Project, update_data: ProjectUpdate) -> Project:
        updated_fields = {
            "name": update_data.name,
            "client_name": update_data.client_name,
            "department": update_data.department,
            "industry": update_data.industry,
            "objective": update_data.objective,
            "status": update_data.status,
        }
        return self._repository.update(project, **updated_fields)

    def delete_project(self, project: Project) -> None:
        self._repository.delete(project)
