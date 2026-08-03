from abc import ABC, abstractmethod
from pathlib import Path

from app.document_processing.models import DocumentType, RawExtraction


class DocumentExtractor(ABC):
    document_type: DocumentType
    supported_extensions: frozenset[str]

    @abstractmethod
    def extract(self, file_path: Path) -> RawExtraction:
        """Extract raw text and format-specific metadata from a document."""

    @staticmethod
    def validate_file(file_path: Path) -> None:
        if not file_path.is_file():
            raise FileNotFoundError(f"Document does not exist: {file_path}")
