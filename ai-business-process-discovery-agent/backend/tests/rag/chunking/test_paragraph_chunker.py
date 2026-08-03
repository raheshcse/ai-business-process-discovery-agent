import pytest

from app.rag.chunking import ParagraphAwareChunker


def test_short_document_produces_one_chunk_with_metadata() -> None:
    text = "A short process description."
    metadata = {"document_type": "txt", "project_id": "project-1"}

    chunks = ParagraphAwareChunker(chunk_size=100, overlap=10).chunk(
        "document-1", text, metadata
    )

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.document_id == "document-1"
    assert chunk.text == text
    assert chunk.chunk_index == 0
    assert chunk.start_character == 0
    assert chunk.end_character == len(text)
    assert chunk.word_count == 4
    assert chunk.metadata == metadata


def test_long_document_produces_ordered_nonempty_chunks() -> None:
    text = " ".join(f"step-{index}" for index in range(50))

    chunks = ParagraphAwareChunker(chunk_size=60, overlap=10).chunk(
        "document-1", text
    )

    assert len(chunks) > 1
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.text for chunk in chunks)
    assert all(len(chunk.text) <= 60 for chunk in chunks)
    assert all(chunk.text == text[chunk.start_character : chunk.end_character] for chunk in chunks)


def test_chunk_end_prefers_paragraph_boundary() -> None:
    first_paragraph = "A" * 30
    second_paragraph = "B" * 30
    text = f"{first_paragraph}\n\n{second_paragraph}"

    chunks = ParagraphAwareChunker(chunk_size=45, overlap=0).chunk(
        "document-1", text
    )

    assert chunks[0].text == first_paragraph
    assert chunks[0].end_character == len(first_paragraph)
    assert chunks[1].text == second_paragraph
    assert chunks[1].start_character == len(first_paragraph) + 2


def test_chunks_include_configured_overlap() -> None:
    text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    chunks = ParagraphAwareChunker(chunk_size=20, overlap=5).chunk(
        "document-1", text
    )

    assert len(chunks) == 3
    for previous, current in zip(chunks, chunks[1:]):
        assert previous.end_character - current.start_character == 5
        assert previous.text[-5:] == current.text[:5]


def test_chunk_ids_are_deterministic_for_same_document_content() -> None:
    chunker = ParagraphAwareChunker(chunk_size=20, overlap=5)
    text = "A deterministic document with enough content for chunks."

    first_run = chunker.chunk("document-1", text)
    second_run = chunker.chunk("document-1", text)
    changed_content = chunker.chunk("document-1", f"{text} Changed.")

    assert [chunk.id for chunk in first_run] == [chunk.id for chunk in second_run]
    assert [chunk.id for chunk in first_run] != [
        chunk.id for chunk in changed_content[: len(first_run)]
    ]


@pytest.mark.parametrize("text", ["", "   ", "\n\n\t"])
def test_empty_or_whitespace_only_input_produces_no_chunks(text: str) -> None:
    chunks = ParagraphAwareChunker(chunk_size=20, overlap=5).chunk(
        "document-1", text
    )

    assert chunks == []


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (-1, 0), (10, -1), (10, 10), (10, 11)],
)
def test_invalid_configuration_is_rejected(chunk_size: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        ParagraphAwareChunker(chunk_size=chunk_size, overlap=overlap)
