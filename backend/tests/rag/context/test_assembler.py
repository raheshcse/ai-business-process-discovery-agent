from app.rag.context import ContextAssembler
from app.rag.vector_store import SearchResult


def result(
    chunk_id: str,
    text: str,
    *,
    document_id: str = "doc-1",
    chunk_index: int = 0,
    score: float = 1.0,
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        document_id=document_id,
        text=text,
        score=score,
        chunk_index=chunk_index,
        metadata={"kind": "policy"},
    )


def test_assembles_multiple_sources_with_markers() -> None:
    assembled = ContextAssembler().assemble(
        [result("a", "First text"), result("b", "Second text")]
    )
    assert assembled.combined_context == (
        "[Source 1]\nFirst text\n\n[Source 2]\nSecond text"
    )
    assert assembled.source_count == 2
    assert assembled.character_count == len(assembled.combined_context)
    assert not assembled.truncated


def test_empty_results_produce_empty_context() -> None:
    assembled = ContextAssembler().assemble([])
    assert assembled.combined_context == ""
    assert assembled.citations == []
    assert assembled.source_count == 0
    assert assembled.character_count == 0
    assert not assembled.truncated


def test_duplicate_chunks_are_ignored() -> None:
    assembled = ContextAssembler().assemble(
        [result("a", "Original"), result("a", "Duplicate")]
    )
    assert assembled.source_count == 1
    assert "Original" in assembled.combined_context
    assert "Duplicate" not in assembled.combined_context


def test_character_limit_keeps_sources_whole() -> None:
    assembled = ContextAssembler(max_characters=16).assemble(
        [result("a", "alpha"), result("b", "beta")]
    )
    assert assembled.combined_context == "[Source 1]\nalpha"
    assert assembled.character_count == 16
    assert assembled.source_count == 1
    assert assembled.truncated


def test_oversized_first_source_is_not_cut() -> None:
    assembled = ContextAssembler(max_characters=12).assemble(
        [result("a", "too long")]
    )
    assert assembled.combined_context == ""
    assert assembled.source_count == 0
    assert assembled.truncated


def test_citations_preserve_ranking_order_and_fields() -> None:
    first = result("high", "High", document_id="doc-2", chunk_index=3, score=0.9)
    second = result("low", "Low", chunk_index=4, score=0.5)
    assembled = ContextAssembler().assemble([first, second])
    assert [citation.chunk_id for citation in assembled.citations] == ["high", "low"]
    assert assembled.citations[0].document_id == "doc-2"
    assert assembled.citations[0].chunk_index == 3
    assert assembled.citations[0].score == 0.9
    assert assembled.citations[0].metadata == {"kind": "policy"}
    assert assembled.citations[0].metadata is not first.metadata


def test_source_markers_follow_included_source_order() -> None:
    assembled = ContextAssembler().assemble(
        [result("a", "A"), result("b", "B"), result("c", "C")]
    )
    assert assembled.combined_context.count("[Source 1]") == 1
    assert assembled.combined_context.count("[Source 2]") == 1
    assert assembled.combined_context.count("[Source 3]") == 1
