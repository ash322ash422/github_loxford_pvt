"""
pipeline.py

Top-level orchestrator: wires L01 -> L04 together across an arbitrary
number of source documents. This is the one place that knows the full
stage order; the CLI entrypoint (scripts/run_pipeline.py) just calls
`run_pipeline`.

Multi-document support: every .txt file in `raw_dir` becomes one
document (document_id = filename stem). Chunking and extraction run
per-document; validation, entity resolution, and canonicalization run
once over the *combined* corpus, which is where cross-document entity
resolution happens.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from L01_chunking import semantic_chunking
from L02_extraction import extract_corpus, save_graph_documents
from L03_1_validation import GraphValidator
from L03_2_entity_resolution import EntityResolver
from L03_3_canonical import build_canonical_graph
from schemas import CanonicalGraph, GraphDocument

logger = logging.getLogger(__name__)


def load_documents(raw_dir: Path) -> List[Dict[str, Any]]:
    """Each .txt file under raw_dir becomes one document; filename stem is its document_id."""
    documents = []
    for path in sorted(Path(raw_dir).glob("*.txt")):
        documents.append({"document_id": path.stem, "text": path.read_text(encoding="utf-8")})
    return documents


def run_pipeline(
    raw_dir: Path,
    output_dir: Path,
    chunk_size: int = 600,
    chunk_overlap: int = 20,
    extraction_chain: Any = None,
    use_extraction_cache: bool = True,
) -> CanonicalGraph:
    """
    Run the full ingestion pipeline over every .txt document in raw_dir.

    Parameters
    ----------
    extraction_chain : optional
        Injectable LLM chain, forwarded to L02.extract_corpus. Leave
        None to use the real OpenAI-backed extractor.
    use_extraction_cache : bool
        If True (default) and `output_dir/L02_extracted_graph_documents.json`
        already exists from a previous run, L02 is skipped entirely and
        that file is loaded instead — no LLM calls, no token cost. This is
        meant for iterating on L03/L04 logic against the same source docs.
        Set False (or delete that file, or pass --refresh-extraction on
        the CLI) once you actually change the source documents or prompt.
        Note: this caches the *whole corpus's* extraction as one unit —
        adding/removing a document invalidates the entire cache, since
        it isn't tracked per-chunk.
    """

    raw_dir = Path(raw_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    documents = load_documents(raw_dir)
    if not documents:
        raise FileNotFoundError(f"No .txt documents found in {raw_dir}")
    logger.info("Loaded %s source document(s) from %s", len(documents), raw_dir)

    # ---- L01: Chunking (per document) ----
    all_chunks: List[Dict[str, Any]] = []
    for doc in documents:
        chunks = semantic_chunking(
            text=doc["text"],
            document_id=doc["document_id"],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        all_chunks.extend(chunks)
    logger.info("Produced %s chunks across %s document(s)", len(all_chunks), len(documents))

    # ---- L02: Extraction (across the whole corpus, cached to disk) ----
    extraction_cache_path = output_dir / "L02_extracted_graph_documents.json"
    graph_documents, failures = extract_corpus(
        all_chunks,
        chain=extraction_chain,
        cache_path=extraction_cache_path,
        use_cache=use_extraction_cache,
    )
    if failures:
        (output_dir / "L02_failed_chunks.json").write_text(
            json.dumps(failures, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.warning("%s chunk(s) failed extraction — see L02_failed_chunks.json", len(failures))

    # ---- L03_1: Validation & normalization ----
    validated = GraphValidator(graph_documents).validate().get_graph_documents()
    save_graph_documents(validated, output_dir / "L03_validated_graph.json")

    # ---- L03_2: Entity resolution (across the whole corpus) ----
    resolved_entities, alias_map = EntityResolver().resolve(validated)

    # ---- L03_3: Canonicalization ----
    canonical_graph = build_canonical_graph(validated, resolved_entities, alias_map)
    (output_dir / "L03_canonical_graph.json").write_text(
        canonical_graph.model_dump_json(indent=2), encoding="utf-8"
    )

    logger.info(
        "Canonical graph: %s entities, %s relationships (%s extraction failures)",
        len(canonical_graph.entities), len(canonical_graph.relationships), len(failures),
    )

    return canonical_graph
