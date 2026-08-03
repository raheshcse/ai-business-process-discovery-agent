from __future__ import annotations

from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project


class ProjectRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, project: Project) -> Project:
        self._session.add(project)
        self._session.flush()
        self._session.commit()
        return project

    def list(self) -> list[Project]:
        statement = select(Project).order_by(Project.created_at.desc())
        result = self._session.execute(statement)
        return result.scalars().all()

    def get(self, project_id: str) -> Project | None:
        statement = select(Project).where(Project.id == project_id)
        result = self._session.execute(statement)
        return result.scalars().first()

    def update(self, project: Project, **updates: str) -> Project:
        for field, value in updates.items():
            if value is not None:
                setattr(project, field, value)
        self._session.flush()
        self._session.commit()
        return project

    def delete(self, project: Project) -> None:
        self._session.delete(project)
        self._session.flush()
        self._session.commit()
