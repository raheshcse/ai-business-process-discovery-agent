from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, document: Document) -> Document:
        self._session.add(document)
        self._session.commit()
        self._session.refresh(document)
        return document

    def list_for_project(self, project_id: str) -> list[Document]:
        statement = (
            select(Document)
            .where(Document.project_id == project_id)
            .order_by(Document.created_at.desc())
        )
        return self._session.execute(statement).scalars().all()

    def get(self, document_id: str) -> Document | None:
        return self._session.get(Document, document_id)

    def delete(self, document: Document) -> None:
        self._session.delete(document)
        self._session.commit()
