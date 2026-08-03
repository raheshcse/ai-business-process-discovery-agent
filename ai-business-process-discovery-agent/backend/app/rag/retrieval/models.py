from dataclasses import dataclass, field
from typing import Any

from app.rag.vector_store import SearchResult


@dataclass(frozen=True)
class RetrievalRequest:
    query: str
    top_k: int = 5
    document_id: str | None = None
    metadata_filters: dict[str, Any] = field(default_factory=dict)
    minimum_score: float | None = None


@dataclass(frozen=True)
class RetrievalResponse:
    query: str
    result_count: int
    provider: str
    model: str
    results: list[SearchResult] = field(default_factory=list)
