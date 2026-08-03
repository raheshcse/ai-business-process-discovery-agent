from app.rag.context.models import AssembledContext, Citation
from app.rag.vector_store import SearchResult


class ContextAssemblyError(ValueError):
    pass


class ContextAssembler:
    def __init__(self, max_characters: int = 12_000) -> None:
        if max_characters <= 0:
            raise ContextAssemblyError("max_characters must be greater than zero")
        self._max_characters = max_characters

    def assemble(self, results: list[SearchResult]) -> AssembledContext:
        sections: list[str] = []
        citations: list[Citation] = []
        seen_chunk_ids: set[str] = set()
        truncated = False

        for result in results:
            if result.chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(result.chunk_id)
            source_number = len(sections) + 1
            section = f"[Source {source_number}]\n{result.text}"
            candidate_length = sum(len(item) for item in sections)
            if sections:
                candidate_length += 2 * len(sections)
            candidate_length += len(section)
            if candidate_length > self._max_characters:
                truncated = True
                break

            sections.append(section)
            citations.append(
                Citation(
                    document_id=result.document_id,
                    chunk_id=result.chunk_id,
                    chunk_index=result.chunk_index,
                    score=result.score,
                    metadata=dict(result.metadata),
                )
            )

        combined_context = "\n\n".join(sections)
        return AssembledContext(
            combined_context=combined_context,
            citations=citations,
            source_count=len(citations),
            character_count=len(combined_context),
            truncated=truncated,
        )
