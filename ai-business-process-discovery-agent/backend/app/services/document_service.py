from __future__ import annotations

import logging
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.integrations.document_storage import DocumentStorage, FileTooLargeError
from app.models.document import Document
from app.repositories.document_repository import DocumentRepository
from app.repositories.project_repository import ProjectRepository

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".txt": {"text/plain"},
    ".csv": {"text/csv", "application/csv", "text/plain"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
}


class ProjectNotFoundError(LookupError):
    pass


class DocumentNotFoundError(LookupError):
    pass


class InvalidDocumentError(ValueError):
    pass


class DocumentTooLargeError(InvalidDocumentError):
    pass


class DocumentService:
    def __init__(
        self,
        session: Session,
        storage: DocumentStorage,
        max_upload_size_bytes: int,
    ) -> None:
        self._documents = DocumentRepository(session)
        self._projects = ProjectRepository(session)
        self._storage = storage
        self._max_upload_size_bytes = max_upload_size_bytes

    async def upload_document(self, project_id: str, file: UploadFile) -> Document:
        if self._projects.get(project_id) is None:
            raise ProjectNotFoundError(project_id)

        # Upload clients sometimes send a Windows path even to a Linux server.
        filename = Path((file.filename or "").replace("\\", "/")).name
        extension = Path(filename).suffix.lower()
        if (
            not filename
            or not Path(filename).stem
            or extension not in ALLOWED_CONTENT_TYPES
        ):
            raise InvalidDocumentError(
                "Unsupported file type. Allowed types: PDF, DOCX, TXT, CSV, XLSX"
            )
        if len(filename) > 255:
            raise InvalidDocumentError("Filename must not exceed 255 characters")

        supplied_type = (file.content_type or "application/octet-stream").lower()
        if (
            supplied_type != "application/octet-stream"
            and supplied_type not in ALLOWED_CONTENT_TYPES[extension]
        ):
            raise InvalidDocumentError(
                f"Content type {supplied_type!r} does not match {extension}"
            )

        try:
            stored = await self._storage.save(
                file,
                extension=extension,
                max_size_bytes=self._max_upload_size_bytes,
            )
        except FileTooLargeError as exc:
            raise DocumentTooLargeError(
                f"File exceeds the maximum size of {self._max_upload_size_bytes} bytes"
            ) from exc

        if stored.size_bytes == 0:
            await self._storage.delete(stored.key)
            raise InvalidDocumentError("Uploaded file must not be empty")

        document = Document(
            project_id=project_id,
            original_filename=filename,
            storage_key=stored.key,
            content_type=supplied_type,
            file_extension=extension,
            size_bytes=stored.size_bytes,
        )
        try:
            created = self._documents.create(document)
        except Exception:
            logger.exception("Failed to save metadata for uploaded file %s", stored.key)
            await self._storage.delete(stored.key)
            raise

        logger.info("Uploaded document %s for project %s", created.id, project_id)
        return created

    def list_documents(self, project_id: str) -> list[Document]:
        if self._projects.get(project_id) is None:
            raise ProjectNotFoundError(project_id)
        return self._documents.list_for_project(project_id)

    def get_document(self, document_id: str) -> Document:
        document = self._documents.get(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)
        return document

    async def delete_document(self, document_id: str) -> None:
        document = self.get_document(document_id)
        await self._storage.delete(document.storage_key)
        self._documents.delete(document)
        logger.info("Deleted document %s", document_id)
