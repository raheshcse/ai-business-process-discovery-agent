from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Citation:
    document_id: str
    chunk_id: str
    chunk_index: int
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssembledContext:
    combined_context: str
    citations: list[Citation] = field(default_factory=list)
    source_count: int = 0
    character_count: int = 0
    truncated: bool = False
