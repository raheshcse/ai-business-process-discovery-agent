import hashlib
import re
from typing import Any, Mapping
from uuid import NAMESPACE_URL, uuid5

from app.rag.chunking.base import DocumentChunker
from app.rag.chunking.models import DocumentChunk


class ParagraphAwareChunker(DocumentChunker):
    """Character-based chunker that prefers paragraph and word boundaries."""

    _paragraph_separator = re.compile(r"\n\s*\n")

    def __init__(self, chunk_size: int = 1000, overlap: int = 200) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if overlap < 0:
            raise ValueError("overlap must not be negative")
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")
        self._chunk_size = chunk_size
        self._overlap = overlap

    def chunk(
        self,
        document_id: str,
        text: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> list[DocumentChunk]:
        content_start = self._next_non_whitespace(text, 0)
        content_end = len(text.rstrip())
        if content_start >= content_end:
            return []

        source_metadata = dict(metadata or {})
        content_digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        paragraph_ends = tuple(
            match.start() for match in self._paragraph_separator.finditer(text)
        )

        chunks: list[DocumentChunk] = []
        start = content_start
        while start < content_end:
            limit = min(start + self._chunk_size, content_end)
            end = self._select_end(text, start, limit, content_end, paragraph_ends)
            chunk_text = text[start:end].rstrip()
            end = start + len(chunk_text)

            if chunk_text:
                chunks.append(
                    DocumentChunk(
                        id=self._build_id(
                            document_id,
                            content_digest,
                            start,
                            end,
                            chunk_text,
                        ),
                        document_id=document_id,
                        text=chunk_text,
                        chunk_index=len(chunks),
                        start_character=start,
                        end_character=end,
                        word_count=len(chunk_text.split()),
                        metadata=dict(source_metadata),
                    )
                )

            if end >= content_end:
                break

            next_start = max(end - self._overlap, start + 1)
            start = self._next_non_whitespace(text, next_start)

        return chunks

    def _select_end(
        self,
        text: str,
        start: int,
        limit: int,
        content_end: int,
        paragraph_ends: tuple[int, ...],
    ) -> int:
        if limit >= content_end:
            return content_end

        minimum_progress = start + self._overlap + 1
        paragraph_candidates = [
            boundary
            for boundary in paragraph_ends
            if minimum_progress <= boundary <= limit
        ]
        if paragraph_candidates:
            return paragraph_candidates[-1]

        word_boundary = text.rfind(" ", minimum_progress, limit + 1)
        if word_boundary > start:
            return word_boundary
        return limit

    @staticmethod
    def _next_non_whitespace(text: str, start: int) -> int:
        while start < len(text) and text[start].isspace():
            start += 1
        return start

    @staticmethod
    def _build_id(
        document_id: str,
        content_digest: str,
        start: int,
        end: int,
        text: str,
    ) -> str:
        identity = f"{document_id}:{content_digest}:{start}:{end}:{text}"
        return str(uuid5(NAMESPACE_URL, identity))
