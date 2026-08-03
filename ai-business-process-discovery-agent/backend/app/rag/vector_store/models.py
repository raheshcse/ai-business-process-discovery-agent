from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    document_id: str
    text: str
    score: float
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)
