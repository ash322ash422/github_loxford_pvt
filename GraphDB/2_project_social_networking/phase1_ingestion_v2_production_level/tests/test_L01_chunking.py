import pytest

from L01_chunking import semantic_chunking


def test_chunks_are_tagged_with_document_id():
    text = "Paragraph one is here.\n\nParagraph two is here."
    chunks = semantic_chunking(text, document_id="doc_a", chunk_size=100, chunk_overlap=0)

    assert len(chunks) == 2
    assert all(c["document_id"] == "doc_a" for c in chunks)


def test_chunk_ids_are_unique_within_a_document():
    text = "\n\n".join([f"This is paragraph number {i}." for i in range(5)])
    chunks = semantic_chunking(text, document_id="doc_b", chunk_size=50, chunk_overlap=0)

    chunk_ids = [c["chunk_id"] for c in chunks]
    assert chunk_ids == sorted(chunk_ids)
    assert len(chunk_ids) == len(set(chunk_ids))


def test_oversized_paragraph_is_split_by_size():
    long_paragraph = "word " * 500  # single paragraph, no blank lines
    chunks = semantic_chunking(long_paragraph, document_id="doc_c", chunk_size=200, chunk_overlap=0)

    assert len(chunks) > 1
    for c in chunks:
        assert c["metadata"]["length"] <= 200 + 20  # small tolerance for split-boundary rounding


def test_missing_document_id_raises():
    with pytest.raises(ValueError):
        semantic_chunking("some text", document_id="")


def test_empty_paragraphs_are_skipped():
    text = "First.\n\n\n\nSecond."
    chunks = semantic_chunking(text, document_id="doc_d", chunk_size=100, chunk_overlap=0)
    assert len(chunks) == 2
