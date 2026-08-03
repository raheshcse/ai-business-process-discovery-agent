from abc import ABC, abstractmethod
from typing import Any, Mapping

from app.rag.chunking.models import DocumentChunk


class DocumentChunker(ABC):
    @abstractmethod
    def chunk(
        self,
        document_id: str,
        text: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> list[DocumentChunk]:
        """Split document text into ordered chunks with source offsets."""
