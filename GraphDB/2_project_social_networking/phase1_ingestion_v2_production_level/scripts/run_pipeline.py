#!/usr/bin/env python3
"""
scripts/run_pipeline.py

CLI entrypoint for the ingestion pipeline. Every .txt file under
--raw-dir is treated as one document; add more files there to run a
multi-document corpus.

Usage
-----
    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --raw-dir data/raw --output-dir output
    python scripts/run_pipeline.py --load-neo4j
    python scripts/run_pipeline.py --load-neo4j --log-level DEBUG
-----
NOTE: When you run python scripts/run_pipeline.py for first time, it may take a few 
minutes to download the required Python packages. After that, subsequent runs are faster.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src" / "ingestion"
sys.path.insert(0, str(SRC_DIR))

from pipeline import run_pipeline  # noqa: E402
from L04_neo4j_loader import Neo4jGraphLoader  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Graph RAG ingestion pipeline.")
    parser.add_argument("--raw-dir", default="data/raw", type=Path, help="Directory of .txt source documents.")
    parser.add_argument("--output-dir", default="output", type=Path, help="Directory for pipeline JSON artifacts.")
    parser.add_argument("--chunk-size", default=600, type=int)
    parser.add_argument("--chunk-overlap", default=20, type=int)
    parser.add_argument("--load-neo4j", action="store_true", help="Also load the canonical graph into Neo4j.")
    parser.add_argument(
        "--refresh-extraction", action="store_true",
        help="Force re-running L02 extraction (ignore any cached L02_extracted_graph_documents.json).",
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    graph = run_pipeline(
        raw_dir=args.raw_dir,
        output_dir=args.output_dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        use_extraction_cache=not args.refresh_extraction,
    )

    print(f"\nEntities      : {len(graph.entities)}")
    print(f"Relationships : {len(graph.relationships)}")

    if args.load_neo4j:
        with Neo4jGraphLoader() as loader:
            loader.create_constraints()
            loader.load_entities(graph.entities)
            loader.load_relationships(graph.relationships)
            loader.verify_graph()


if __name__ == "__main__":
    main()


""" 2 runs back to back with the same input files (no changes) and caching enabled:

# 2026-07-30 19:56:21,164 INFO httpx — HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
# 2026-07-30 19:56:54,941 INFO httpx — HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
# 2026-07-30 19:57:22,164 INFO httpx — HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
# 2026-07-30 19:57:22,177 INFO L02_extraction — Saved 6 extracted graph document(s) to output\L02_extracted_graph_documents.json
# 2026-07-30 19:57:22,189 INFO L02_extraction — Saved 6 extracted graph document(s) to output\L03_validated_graph.json
# 2026-07-30 19:57:22,210 INFO pipeline — Canonical graph: 13 entities, 36 relationships (0 extraction failures)

# Entities      : 13
# Relationships : 36
# (.venv) PS C:\Users\hi\Desktop\projects\python_projects\tutorial\play_langchain_llamaindex_langgraph\2_project_social_networking\phase1_ingestion_v3> python scripts/run_pipeline.py
# 2026-07-30 20:11:30,986 INFO pipeline — Loaded 2 source document(s) from data\raw
# 2026-07-30 20:11:30,987 INFO pipeline — Produced 6 chunks across 2 document(s)
# 2026-07-30 20:11:30,987 INFO L02_extraction — Extraction cache hit at output\L02_extracted_graph_documents.json — skipping LLM calls for 6 chunk(s). Delete this file or pass use_cache=False to force re-extraction.
# 2026-07-30 20:11:30,989 INFO L02_extraction — Loaded 6 cached extracted graph document(s) from output\L02_extracted_graph_documents.json
# 2026-07-30 20:11:30,993 INFO L02_extraction — Saved 6 extracted graph document(s) to output\L03_validated_graph.json
# 2026-07-30 20:11:30,997 INFO pipeline — Canonical graph: 13 entities, 36 relationships (0 extraction failures)

# Entities      : 13
# Relationships : 36

"""