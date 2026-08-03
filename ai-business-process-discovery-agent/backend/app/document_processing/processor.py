import logging
from collections.abc import Iterable
from pathlib import Path

from app.document_processing.base import DocumentExtractor
from app.document_processing.extractors import (
    CsvExtractor,
    DocxExtractor,
    PdfExtractor,
    TxtExtractor,
    XlsxExtractor,
)
from app.document_processing.metadata import MetadataExtractor
from app.document_processing.models import DocumentExtractionResult, ExtractionStatus
from app.document_processing.normalizer import TextNormalizer

logger = logging.getLogger(__name__)


class UnsupportedDocumentTypeError(ValueError):
    pass


class DocumentProcessor:
    def __init__(
        self,
        extractors: Iterable[DocumentExtractor] | None = None,
        normalizer: TextNormalizer | None = None,
        metadata_extractor: MetadataExtractor | None = None,
    ) -> None:
        configured_extractors = (
            extractors
            if extractors is not None
            else (
                PdfExtractor(),
                DocxExtractor(),
                TxtExtractor(),
                CsvExtractor(),
                XlsxExtractor(),
            )
        )
        self._extractors = {
            extension: extractor
            for extractor in configured_extractors
            for extension in extractor.supported_extensions
        }
        self._normalizer = normalizer or TextNormalizer()
        self._metadata_extractor = metadata_extractor or MetadataExtractor()

    def process(
        self,
        file_path: Path,
        file_type: str | None = None,
    ) -> DocumentExtractionResult:
        extension = self._normalize_extension(file_type or file_path.suffix)
        extractor = self._extractors.get(extension)
        if extractor is None:
            raise UnsupportedDocumentTypeError(
                f"Unsupported document type: {extension or '<missing>'}"
            )

        try:
            raw = extractor.extract(file_path)
            text = self._normalizer.normalize(raw.text)
            metadata = self._metadata_extractor.extract(
                text,
                extractor.document_type,
                raw.page_count,
            )
            return DocumentExtractionResult(
                text=text,
                metadata=metadata,
                extraction_status=ExtractionStatus.SUCCESS,
            )
        except Exception:
            logger.exception(
                "Document extraction failed for %s using %s",
                file_path,
                extractor.__class__.__name__,
            )
            return DocumentExtractionResult(
                text="",
                metadata=self._metadata_extractor.extract(
                    "", extractor.document_type, None
                ),
                extraction_status=ExtractionStatus.FAILED,
            )

    @staticmethod
    def _normalize_extension(file_type: str) -> str:
        normalized = file_type.strip().lower()
        if not normalized or normalized.startswith("."):
            return normalized
        return f".{normalized}"
