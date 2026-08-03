from app.document_processing.models import DocumentType, ExtractionMetadata


class MetadataExtractor:
    def extract(
        self,
        text: str,
        document_type: DocumentType,
        page_count: int | None = None,
    ) -> ExtractionMetadata:
        return ExtractionMetadata(
            page_count=page_count,
            character_count=len(text),
            word_count=len(text.split()),
            detected_document_type=document_type,
        )
