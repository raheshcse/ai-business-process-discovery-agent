from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EmbeddedChunk:
    chunk_id: str
    document_id: str
    text: str
    embedding: list[float]
    chunk_index: int
    metadata: dict[str, Any]
    provider: str
    model: str
