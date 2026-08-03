from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DocumentChunk:
    id: str
    document_id: str
    text: str
    chunk_index: int
    start_character: int
    end_character: int
    word_count: int
    metadata: dict[str, Any] = field(default_factory=dict)
