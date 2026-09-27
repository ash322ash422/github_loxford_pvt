# Graph RAG Ingestion Pipeline

Phase 1 ingestion for a Graph RAG system: 

raw documents -> chunks -> LLM-extracted entities/relationships -> validated -> entity-resolved -> canonicalized -> loaded into Neo4j.

## Project layout

```
graph_rag_ingestion/
├── config/
│   └── settings.py            # centralized env-var config
├── src/ingestion/
│   ├── schemas.py              # Pydantic contracts (extraction-time + resolved/canonical)
│   ├── L01_chunking.py         # Stage 1: document -> chunks
│   ├── L02_extraction.py       # Stage 2: chunk -> entities/relationships (LLM)
│   ├── L03_1_validation.py     # Stage 3a: schema + label + relation validation
│   ├── L03_2_entity_resolution.py  # Stage 3b: cross-document entity resolution
│   ├── L03_3_canonical.py      # Stage 3c: build final de-duplicated graph
│   ├── L04_neo4j_loader.py     # Stage 4: batched, idempotent Neo4j writes
│   └── pipeline.py             # orchestrator wiring L01 -> L04
├── scripts/
│   ├── run_pipeline.py         # CLI entrypoint
│   └── verify_neo4j_connectivity.py
├── data/raw/                   # input documents (one .txt = one document)
├── output/                     # pipeline JSON artifacts (gitignored)
├── tests/                      # pytest suite, 34 tests, no network required
├── requirements.txt
├── .env.example
└── pytest.ini
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your real OpenAI + Neo4j Aura credentials
```

## Running

```bash
# Sanity-check your Neo4j credentials before a full run
python scripts/verify_neo4j_connectivity.py

# Chunk -> extract -> validate -> resolve -> canonicalize; writes JSON to output/
python scripts/run_pipeline.py

# Same, plus load the result into Neo4j
python scripts/run_pipeline.py --load-neo4j

# Multiple documents: just drop more .txt files into data/raw/ —
# the filename stem becomes the document_id.
python scripts/run_pipeline.py --raw-dir data/raw --output-dir output

```

### Extraction caching (saves LLM cost during dev/test)

`output/L02_extracted_graph_documents.json` doubles as a cache: the first
run calls the LLM and writes extraction results there; every run after that
loads straight from the file and **skips the LLM entirely**, as long as the
file still exists. This means you can iterate on L03/L04 logic freely
without re-paying for extraction.

```bash
# Force a real re-extraction (e.g. you changed the source docs or the prompt)
python scripts/run_pipeline.py --refresh-extraction

# ...or just delete the cache file yourself
rm output/L02_extracted_graph_documents.json
```

Note this caches the *whole corpus* as one file, not per-chunk — adding or
removing a document invalidates the entire cache, since staleness isn't
tracked per-chunk.

## Testing

```bash
pytest
```

34 tests, all offline — the LLM call is dependency-injected (`chain=`) so
extraction and full-pipeline tests run against canned responses instead of
hitting OpenAI, and the Neo4j loader tests run against a mocked driver
instead of a real database. No API key or database needed to run the suite.

## What changed from the prototype (and why)

| Capability | What it does now |
|---|---|
| **Entity resolution** | `L03_2_entity_resolution.py` — blocking (label + name-prefix) + fuzzy name similarity + union-find clustering, so "TechHub" in one document and "Tech Hub" in another resolve to a single node instead of two. The old pipeline only did exact-id matching, which breaks the moment the LLM assigns a different id/spelling across documents. |
| **Provenance** | Every `ResolvedEntity` and `CanonicalRelationship` now carries a `mentions: List[Mention]` — the exact `(document_id, chunk_id)` pairs that support it, plus the surface form seen. `evidence_count` tells you how many independent mentions back a relationship. The old canonical graph discarded this entirely. |
| **Neo4j writes** | Batched via `UNWIND` (configurable `batch_size`, default 500) instead of one transaction per row. Transient errors (`ServiceUnavailable`, `TransientError`) retry with exponential backoff. Still idempotent (`MERGE` on `canonical_id`), still defends against Cypher injection by only interpolating whitelisted label/relation names. |
| **Multi-document support** | `GraphDocument` now carries a `document_id`; `pipeline.py` treats every `.txt` in `data/raw/` as a separate document, chunks/extracts each independently, then runs entity resolution and canonicalization once over the *combined* corpus — which is where cross-document merging happens. |
| **Tests** | 40 pytest tests across all five modules plus offline integration tests proving two documents with a spelling variant resolve into one entity end-to-end. |
| **Extraction caching** | `extract_corpus(..., cache_path=...)` in `L02_extraction.py` writes extraction results to disk and loads from there on subsequent runs instead of calling the LLM again — `pipeline.py` wires this to `output/L02_extracted_graph_documents.json` automatically. Use `--refresh-extraction` on the CLI (or delete that file) to force a real re-extraction. |

Also fixed along the way:
- The syntax error in the original `L02_extraction.py` (trailing comma on the `schemas` import) that made the file unparseable.
- The `group_team` / "the team" generic-entity leak — `remove_generic_entities()` is now implemented and enabled (it existed as a commented-out no-op before).
- Extraction now retries transient LLM failures and isolates permanent ones into a per-run `L02_failed_chunks.json` dead-letter file instead of crashing the whole batch.
- The OpenAI/Neo4j clients are constructed lazily, so importing any module — and running the test suite — never requires network access or API keys.

## Known follow-ups (not done in this pass)

- **Entity resolution is name-similarity based, not embedding-based.** It's dependency-free and fully unit-testable, but will under-merge cases with no lexical overlap (e.g. "TechHub" vs. an abbreviation "TH" used elsewhere). If that shows up in real data, swap in an embedding-similarity `similarity_fn` — the `EntityResolver` constructor already accepts one.
- **Semantic redundancy across relation types** (e.g. `CEO_OF` and `MANAGES` both extracted for the same pair) isn't collapsed — that's a prompt/ontology decision (should `CEO_OF` imply `MANAGES` or replace it?) rather than a pipeline bug, worth deciding deliberately.
- **No structured logging/metrics export** (still Python `logging`, not shipped to anything) and **no CI config** — add both before calling this production-deployed rather than production-*structured*.
- **Chunking is paragraph + recursive-character-split, not embedding-based semantic chunking** — fine for now, worth revisiting if extraction quality suffers on longer, less paragraph-structured documents.
