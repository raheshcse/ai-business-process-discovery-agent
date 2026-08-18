"""Turn an uploaded file into retrievable evidence.

Uploading previously stored bytes and a database row and stopped there --
nothing extracted, chunked or indexed them, so retrieval had nothing to
find. This service is that missing step.

Chunk metadata carries `project_id` deliberately: the governance monitors
in `app.governance.process_discovery.monitors` reject any citation whose
`metadata["project_id"]` does not match the project under analysis, so
omitting it would cause every run to be blocked at the first gate.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.composition import (
    get_chunker,
    get_document_processor,
    get_rag_service,
)
from app.core.config import settings
from app.document_processing import ExtractionStatus, UnsupportedDocumentTypeError
from app.models.document import Document, DocumentIndexStatus
from app.rag.embeddings import EmbeddingProviderUnavailableError
from app.repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)

def _no_text_message(extension: str) -> str:
    """Explain an empty extraction in terms the uploader can act on.

    "The document contains no readable text" is accurate and useless: it
    describes the symptom without naming the overwhelmingly common cause,
    which for a PDF is that the pages are scanned images.
    """
    if extension == ".pdf":
        return (
            "This PDF has no text layer -- its pages are images, which is what "
            "a scan or a photographed document produces. This application does "
            "not perform OCR, so there is nothing to analyse. Re-export the "
            "file with selectable text, or run it through an OCR tool first."
        )
    if extension in {".csv", ".xlsx"}:
        return (
            "This spreadsheet has no readable cell content. It may be empty, "
            "or contain only images, charts or formatting."
        )
    return (
        "This document contains no readable text. It may be empty, or hold "
        "only images."
    )


def _extraction_failed_message(extension: str) -> str:
    if extension == ".pdf":
        return (
            "This PDF could not be opened. It may be password-protected, "
            "corrupt, or use an unsupported encryption scheme."
        )
    return (
        f"This {extension.lstrip('.').upper()} file could not be read. It may "
        "be corrupt, password-protected, or not really a "
        f"{extension.lstrip('.').upper()} file despite its extension."
    )


# Serialises mutations of the process-wide in-memory vector store. Indexing
# runs as a background task, so two concurrent uploads would otherwise race
# on `add_chunks`.
_index_lock = asyncio.Lock()


class IndexingService:
    def __init__(self, session: Session, uploads_directory: Path | None = None) -> None:
        self._session = session
        self._documents = DocumentRepository(session)
        self._root = Path(
            uploads_directory
            if uploads_directory is not None
            else settings.uploads_directory
        ).resolve()

    async def index_document(self, document_id: str) -> None:
        """Extract, chunk and index one document, recording status.

        Never raises: a failed document must leave the rest of the project
        usable and must surface a readable reason in the UI.
        """
        document = self._documents.get(document_id)
        if document is None:
            logger.warning("Cannot index unknown document %s", document_id)
            return

        self._set_status(document, DocumentIndexStatus.PROCESSING)
        path = self._root / document.storage_key

        try:
            if not path.exists():
                raise FileNotFoundError(
                    "The stored file is missing from the uploads directory."
                )
            extraction = await asyncio.to_thread(
                get_document_processor().process, path, document.file_extension
            )
            if extraction.extraction_status is ExtractionStatus.FAILED:
                raise ValueError(_extraction_failed_message(document.file_extension))
            if not extraction.text.strip():
                raise ValueError(_no_text_message(document.file_extension))

            chunks = await asyncio.to_thread(
                get_chunker().chunk,
                document.id,
                extraction.text,
                {
                    "project_id": document.project_id,
                    "document_id": document.id,
                    "filename": document.original_filename,
                    "file_extension": document.file_extension,
                    "document_type": extraction.metadata.detected_document_type.value,
                },
            )
            if not chunks:
                raise ValueError("The document produced no indexable content.")

            rag_service = get_rag_service()
            async with _index_lock:
                # Re-indexing must not duplicate chunks for this document.
                await asyncio.to_thread(rag_service.delete_by_document, document.id)
                result = await asyncio.to_thread(rag_service.index_chunks, chunks)

            document.index_status = DocumentIndexStatus.INDEXED.value
            document.index_error = None
            document.indexed_at = datetime.now(timezone.utc)
            document.page_count = extraction.metadata.page_count
            document.word_count = extraction.metadata.word_count
            document.character_count = extraction.metadata.character_count
            document.chunk_count = result.indexed_count
            document.detected_document_type = (
                extraction.metadata.detected_document_type.value
            )
            self._session.commit()
            logger.info(
                "Indexed document %s into %s chunks", document.id, result.indexed_count
            )
        except UnsupportedDocumentTypeError:
            self._fail(document, "This file type cannot be processed.")
        except FileNotFoundError as exc:
            self._fail(document, str(exc))
        except EmbeddingProviderUnavailableError as exc:
            # Not a ValueError, so without this branch it fell through to the
            # generic handler below and the user saw "check the server logs"
            # for a cause the provider had already described precisely.
            self._fail(document, str(exc))
        except ValueError as exc:
            self._fail(document, str(exc))
        except Exception:
            # The exception text may contain provider or filesystem detail,
            # so the stored message stays generic and the detail goes to logs.
            logger.exception("Indexing failed for document %s", document_id)
            self._fail(
                document,
                "Indexing failed unexpectedly. Check the server logs for detail.",
            )

    async def remove_document(self, document_id: str) -> None:
        """Drop a document's chunks from the vector store."""
        async with _index_lock:
            await asyncio.to_thread(
                get_rag_service().delete_by_document, document_id
            )

    async def reindex_project(self, project_id: str) -> int:
        documents = self._documents.list_for_project(project_id)
        for document in documents:
            await self.index_document(document.id)
        return len(documents)

    def _set_status(self, document: Document, status: DocumentIndexStatus) -> None:
        document.index_status = status.value
        self._session.commit()

    def _fail(self, document: Document, message: str) -> None:
        document.index_status = DocumentIndexStatus.FAILED.value
        document.index_error = message
        document.chunk_count = 0
        self._session.commit()
        logger.warning("Document %s failed indexing: %s", document.id, message)
