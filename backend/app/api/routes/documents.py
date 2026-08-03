from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.integrations.document_storage import DocumentStorage, LocalDocumentStorage
from app.schemas.document import DocumentResponse
from app.services.document_service import (
    DocumentNotFoundError,
    DocumentService,
    DocumentTooLargeError,
    InvalidDocumentError,
    ProjectNotFoundError,
)
from app.services.indexing_service import IndexingService

router = APIRouter(tags=["Documents"])


@lru_cache
def get_document_storage() -> DocumentStorage:
    return LocalDocumentStorage(Path(settings.uploads_directory))


def get_document_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[DocumentStorage, Depends(get_document_storage)],
) -> DocumentService:
    return DocumentService(db, storage, settings.max_upload_size_bytes)


DocumentServiceDependency = Annotated[DocumentService, Depends(get_document_service)]


async def _index_in_background(document_id: str) -> None:
    """Own the session: the request-scoped one is closed by then."""
    session = SessionLocal()
    try:
        await IndexingService(session).index_document(document_id)
    finally:
        session.close()


async def _remove_from_index(document_id: str) -> None:
    session = SessionLocal()
    try:
        await IndexingService(session).remove_document(document_id)
    finally:
        session.close()


@router.post(
    "/projects/{project_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    project_id: str,
    file: Annotated[UploadFile, File(description="Document to upload")],
    service: DocumentServiceDependency,
    background_tasks: BackgroundTasks,
) -> DocumentResponse:
    try:
        document = await service.upload_document(project_id, file)
    except ProjectNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found") from exc
    except DocumentTooLargeError as exc:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(exc)) from exc
    except InvalidDocumentError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    # Extraction and indexing run after the response so a large PDF never
    # holds the upload request open. The client polls `index_status`.
    background_tasks.add_task(_index_in_background, document.id)
    return document


@router.get("/projects/{project_id}/documents", response_model=list[DocumentResponse])
def list_documents(
    project_id: str,
    service: DocumentServiceDependency,
) -> list[DocumentResponse]:
    try:
        return service.list_documents(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found") from exc


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    service: DocumentServiceDependency,
) -> DocumentResponse:
    try:
        return service.get_document(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found") from exc


@router.post(
    "/documents/{document_id}/reindex",
    response_model=DocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def reindex_document(
    document_id: str,
    service: DocumentServiceDependency,
    background_tasks: BackgroundTasks,
) -> DocumentResponse:
    """Retry extraction and indexing for a document that failed."""
    try:
        document = service.get_document(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found") from exc
    background_tasks.add_task(_index_in_background, document_id)
    return document


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    service: DocumentServiceDependency,
    background_tasks: BackgroundTasks,
) -> None:
    try:
        await service.delete_document(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found") from exc
    # Drop the chunks too, otherwise deleted content stays retrievable.
    background_tasks.add_task(_remove_from_index, document_id)
