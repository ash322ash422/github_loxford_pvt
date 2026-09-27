"""
L01_chunking.py

Stage 1: split a raw document into semantically-bounded, size-capped
chunks ready for LLM extraction.

Each chunk is tagged with `document_id` (caller-supplied, stable across
the whole pipeline) and a `chunk_id` that is unique *within that
document*. Downstream stages use the pair (document_id, chunk_id) as
the provenance key, so multi-document corpora never collide.
"""

from __future__ import annotations

from typing import Any, Dict, List

from langchain_text_splitters import RecursiveCharacterTextSplitter


def semantic_chunking(
    text: str,
    document_id: str,
    chunk_size: int = 600,
    chunk_overlap: int = 50,
) -> List[Dict[str, Any]]:
    """
    Parameters
    ----------
    text : str
        Raw input document.
    document_id : str
        Stable identifier for this document (e.g. filename stem).
    chunk_size : int
        Maximum chunk size.
    chunk_overlap : int
        Overlap between adjacent chunks.

    Returns
    -------
    List[Dict] — each dict has document_id, chunk_id, text, metadata.
    """

    if not document_id:
        raise ValueError("document_id is required for provenance tracking.")

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ". ", " "],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    chunks: List[Dict[str, Any]] = []
    chunk_counter = 1

    for paragraph_number, paragraph in enumerate(paragraphs, start=1):
        for chunk_index, chunk in enumerate(splitter.split_text(paragraph), start=1):
            chunks.append(
                {
                    "document_id": document_id,
                    "chunk_id": chunk_counter,
                    "text": chunk,
                    "metadata": {
                        "paragraph": paragraph_number,
                        "chunk_index": chunk_index,
                        "length": len(chunk),
                    },
                }
            )
            chunk_counter += 1

    return chunks


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sample_path = Path(__file__).resolve().parents[2] / "data" / "raw" / "doc_001.txt"
    sample_text = sample_path.read_text(encoding="utf-8")

    result = semantic_chunking(sample_text, document_id="doc_001", chunk_size=600, chunk_overlap=20)
    for chunk in result:
        print(f"[{chunk['document_id']}#{chunk['chunk_id']}] {chunk['text']}")
        print()


"""
[doc_001#1] TechHub is a major software company managed by its CEO, Alice. The company developed a popular messaging application called ChatApp. Alice closely manages Bob, who works as the Lead Developer for ChatApp. Bob is married to Charlie, a Product Designer who also works at TechHub. Charlie shares an office with Diana, a Data Scientist at the company.

[doc_001#2] Beyond work, this group forms a tight social circle. Alice, Bob, and Charlie are all members of a professional organization called TechAssociation. Diana recently joined this same organization. Socially, Bob and Diana are co-organizers of a local community group called DataClub. Charlie is also a member of DataClub, where she frequently interacts with Diana.

[doc_001#3] The team heavily utilizes online platforms. Bob regularly follows Diana on GitHub to review her open-source code. Meanwhile, Diana follows Charlie on Behance to look at her design portfolios. Both Bob and Charlie are active users of LinkedIn for professional networking. Alice also uses LinkedIn, where she frequently views posts by Bob and Charlie. Additionally, TechHub maintains an official corporate profile on LinkedIn to post company updates.
"""