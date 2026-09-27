"""
L02_extraction.py

Stage 2: LLM-based, schema-constrained entity/relationship extraction.

Design notes
------------
* The OpenAI client is built lazily (`get_default_chain`), not at import
  time — importing this module never requires network access or an API
  key, which is what makes it possible to unit test `extract_graph`
  fully offline (pass in a fake `chain`).
* `extract_graph` retries transient failures with exponential backoff.
* `extract_corpus` processes a whole multi-document chunk list and
  never lets one bad chunk kill the run — failures are collected into
  a dead-letter list for later inspection/retry instead.
* `extract_corpus(..., cache_path=...)` saves extraction results to disk
  as JSON, and on a later call with the same cache_path loads from that
  file instead of calling the LLM again. This is purely a dev/test cost
  saver: while you're iterating on L03/L04 logic against the same source
  documents, you don't pay for re-extraction every run. Delete the cache
  file (or pass use_cache=False / --refresh-extraction on the CLI) once
  you actually change the source documents or the extraction prompt.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate

from schemas import ExtractionResult, GraphDocument

load_dotenv()
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("EXTRACTION_MODEL", "gpt-5")

EXTRACTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
    You are an expert Knowledge Graph extraction engine.

    Extract every entity and every relationship.

    Rules

    1. Return only entities that appear explicitly.
    2. Do not hallucinate.
    3. Every entity must have

    - id
    - name
    - label

    4. Entity IDs MUST follow this format

    person_alice
    person_bob
    organization_techhub
    group_dataclub
    platform_github
    product_chatapp

    Never use dots.
    Never use spaces.
    Use lowercase.
    Use underscore.

    5. Labels must be one of

    Person
    Organization
    Product
    Platform
    Group

    6. Every relationship must have

    source
    target
    relation

    7. Relation names MUST be uppercase.

    Examples

    MANAGES
    WORKS_AT
    WORKS_ON
    MEMBER_OF
    MARRIED_TO
    USES_PLATFORM
    FOLLOWS
    DEVELOPED

    8. Do NOT extract generic/non-specific references as entities
       (e.g. "the team", "the group", "the company", "staff").
       Only extract specific, named entities.

    Return every relationship you can infer directly from the text.
""",
        ),
        ("human", "{text}"),
    ]
)

# Lazily constructed so importing this module never needs network/API access.
_default_chain = None


def get_default_chain():
    global _default_chain
    if _default_chain is None:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(api_key=OPENAI_API_KEY, model=MODEL_NAME, temperature=0)
        structured_llm = llm.with_structured_output(ExtractionResult)
        _default_chain = EXTRACTION_PROMPT | structured_llm
    return _default_chain


def extract_graph(
    chunk: Dict[str, Any],
    chain: Optional[Any] = None,
    max_retries: int = 3,
    retry_backoff_seconds: float = 2.0,
) -> GraphDocument:
    """
    Extract a GraphDocument from one chunk, retrying transient failures.

    Parameters
    ----------
    chunk : dict
        Must contain document_id, chunk_id, text (see L01_chunking output).
    chain : Any, optional
        Injectable LangChain runnable exposing `.invoke({"text": ...}) ->
        ExtractionResult`. Defaults to the real OpenAI-backed chain.
        Tests pass a fake chain here to avoid network calls.
    """

    active_chain = chain or get_default_chain()

    attempt = 0
    while True:
        try:
            result: ExtractionResult = active_chain.invoke({"text": chunk["text"]})
            return GraphDocument(
                document_id=chunk["document_id"],
                chunk_id=chunk["chunk_id"],
                entities=result.entities,
                relationships=result.relationships,
            )
        except Exception as exc:  # noqa: BLE001 — deliberately broad: any LLM/network failure is retryable
            attempt += 1
            if attempt > max_retries:
                logger.error(
                    "Extraction failed for %s#%s after %s attempts: %s",
                    chunk["document_id"], chunk["chunk_id"], attempt - 1, exc,
                )
                raise
            sleep_for = retry_backoff_seconds * (2 ** (attempt - 1))
            logger.warning(
                "Extraction error on %s#%s (attempt %s/%s): %s — retrying in %.1fs",
                chunk["document_id"], chunk["chunk_id"], attempt, max_retries, exc, sleep_for,
            )
            time.sleep(sleep_for)


def save_graph_documents(graph_documents: List[GraphDocument], path: Union[str, Path]) -> None:
    """Serialize extracted GraphDocuments to JSON on disk (L03 can load this directly)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([g.model_dump(mode="json") for g in graph_documents], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Saved %s extracted graph document(s) to %s", len(graph_documents), path)


def load_graph_documents(path: Union[str, Path]) -> List[GraphDocument]:
    """Load previously-saved GraphDocuments from JSON on disk."""
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    graph_documents = [GraphDocument(**item) for item in raw]
    logger.info("Loaded %s cached extracted graph document(s) from %s", len(graph_documents), path)
    return graph_documents


def extract_corpus(
    chunks: List[Dict[str, Any]],
    chain: Optional[Any] = None,
    continue_on_error: bool = True,
    cache_path: Optional[Union[str, Path]] = None,
    use_cache: bool = True,
) -> Tuple[List[GraphDocument], List[Dict[str, Any]]]:
    """
    Extract GraphDocuments for a whole (possibly multi-document) chunk list.

    Parameters
    ----------
    cache_path : str or Path, optional
        If given and the file already exists and use_cache=True, extraction
        results are loaded from this file and the LLM is never called —
        this is the token-cost saver for iterative dev/test runs. If the
        file doesn't exist yet, extraction runs normally and the results
        are written there afterward, ready for next time.
    use_cache : bool
        Set False to force re-extraction even if a cache file exists
        (e.g. after changing the source documents or the prompt).

    Returns
    -------
    (graph_documents, failures) — failures is a dead-letter list of
    {..chunk fields.., "error": str} for chunks that failed even after
    retries, so one bad chunk in a 500-document run doesn't lose the
    other 499. failures is always [] when results come from cache.
    """

    if cache_path is not None:
        cache_path = Path(cache_path)
        if use_cache and cache_path.exists():
            logger.info(
                "Extraction cache hit at %s — skipping LLM calls for %s chunk(s). "
                "Delete this file or pass use_cache=False to force re-extraction.",
                cache_path, len(chunks),
            )
            return load_graph_documents(cache_path), []

    graph_documents: List[GraphDocument] = []
    failures: List[Dict[str, Any]] = []

    for chunk in chunks:
        try:
            graph_documents.append(extract_graph(chunk, chain=chain))
        except Exception as exc:  # noqa: BLE001
            failures.append({**chunk, "error": str(exc)})
            if not continue_on_error:
                raise

    if cache_path is not None:
        save_graph_documents(graph_documents, cache_path)

    return graph_documents, failures
