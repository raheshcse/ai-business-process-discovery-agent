from dataclasses import dataclass
from enum import Enum


class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    CSV = "csv"
    XLSX = "xlsx"


class ExtractionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True)
class RawExtraction:
    text: str
    page_count: int | None = None


@dataclass(frozen=True)
class ExtractionMetadata:
    page_count: int | None
    character_count: int
    word_count: int
    detected_document_type: DocumentType


@dataclass(frozen=True)
class DocumentExtractionResult:
    text: str
    metadata: ExtractionMetadata
    extraction_status: ExtractionStatus
