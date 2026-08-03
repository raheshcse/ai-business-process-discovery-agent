from pathlib import Path

import pytest

from app.document_processing.base import DocumentExtractor
from app.document_processing.models import (
    DocumentType,
    ExtractionStatus,
    RawExtraction,
)
from app.document_processing.normalizer import TextNormalizer
from app.document_processing.processor import (
    DocumentProcessor,
    UnsupportedDocumentTypeError,
)


class StubTxtExtractor(DocumentExtractor):
    document_type = DocumentType.TXT
    supported_extensions = frozenset({".txt"})

    def extract(self, file_path: Path) -> RawExtraction:
        return RawExtraction("  First\r\nline   \r\n\r\n\r\nSecond line  ")


class FailingTxtExtractor(StubTxtExtractor):
    def extract(self, file_path: Path) -> RawExtraction:
        raise OSError("Unreadable document")


def test_normalizer_cleans_line_endings_spaces_and_blank_lines() -> None:
    text = "  First\r\nline   \r\n\r\n\r\nSecond\tline  "

    result = TextNormalizer().normalize(text)

    assert result == "First\nline\n\nSecond line"


def test_processor_selects_extractor_and_builds_metadata(tmp_path: Path) -> None:
    processor = DocumentProcessor(extractors=[StubTxtExtractor()])

    result = processor.process(tmp_path / "document.TXT")

    assert result.text == "First\nline\n\nSecond line"
    assert result.extraction_status is ExtractionStatus.SUCCESS
    assert result.metadata.detected_document_type is DocumentType.TXT
    assert result.metadata.character_count == len(result.text)
    assert result.metadata.word_count == 4
    assert result.metadata.page_count is None


def test_processor_accepts_explicit_file_type(tmp_path: Path) -> None:
    processor = DocumentProcessor(extractors=[StubTxtExtractor()])

    result = processor.process(tmp_path / "opaque-storage-key", file_type="txt")

    assert result.extraction_status is ExtractionStatus.SUCCESS


def test_processor_returns_failed_result_when_extraction_fails(
    tmp_path: Path,
) -> None:
    processor = DocumentProcessor(extractors=[FailingTxtExtractor()])

    result = processor.process(tmp_path / "document.txt")

    assert result.text == ""
    assert result.extraction_status is ExtractionStatus.FAILED
    assert result.metadata.character_count == 0
    assert result.metadata.word_count == 0


def test_processor_rejects_unsupported_document_type(tmp_path: Path) -> None:
    processor = DocumentProcessor(extractors=[StubTxtExtractor()])

    with pytest.raises(UnsupportedDocumentTypeError):
        processor.process(tmp_path / "document.json")
