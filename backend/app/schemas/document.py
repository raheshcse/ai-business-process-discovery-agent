from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentIndexStatus


class DocumentResponse(BaseModel):
    """Uploaded document plus its RAG indexing state.

    The indexing fields are additive; every field the original response
    carried is unchanged, so existing consumers are unaffected.
    """

    id: str
    project_id: str
    original_filename: str
    content_type: str
    file_extension: str
    size_bytes: int
    created_at: datetime

    index_status: DocumentIndexStatus = DocumentIndexStatus.PENDING
    index_error: str | None = None
    indexed_at: datetime | None = None
    page_count: int | None = None
    word_count: int | None = None
    character_count: int | None = None
    chunk_count: int | None = None
    detected_document_type: str | None = None

    model_config = ConfigDict(from_attributes=True)
