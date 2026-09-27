"""
L04_neo4j_loader.py

Stage 4: Neo4j Graph Ingestion

Production-oriented loader:

* Batched writes via UNWIND (one round-trip per batch, not per row).
* Retries transient connection errors with exponential backoff.
* MERGE-keyed on `canonical_id` => idempotent, safe to re-run the whole
  pipeline against the same database without creating duplicates.
* Writes provenance (aliases, mention/evidence counts, source doc#chunk
  ids) onto nodes/edges as properties.
* Defends against Cypher injection from label/relation names by only
  ever interpolating values that are in the schema's fixed whitelists
  (labels/relations can't be parameterized in Cypher, so whitelisting
  is the standard mitigation) — anything else is skipped and logged.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Dict, List

from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, TransientError

from schemas import CanonicalRelationship, ResolvedEntity, VALID_ENTITY_LABELS, VALID_RELATIONS

load_dotenv()
logger = logging.getLogger(__name__)


class Neo4jGraphLoader:
    """Batched, retrying, idempotent Neo4j writer for a CanonicalGraph."""

    def __init__(
        self,
        uri: str = None,
        username: str = None,
        password: str = None,
        database: str = None,
        batch_size: int = 500,
        max_retries: int = 3,
        retry_backoff_seconds: float = 1.0,
    ):
        self.uri = uri or os.getenv("NEO4J_URI")
        self.username = username or os.getenv("NEO4J_USERNAME")
        self.password = password or os.getenv("NEO4J_PASSWORD")
        self.database = database or os.getenv("NEO4J_DATABASE", "neo4j")
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.driver = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
        self.driver.verify_connectivity()
        logger.info("Connected to Neo4j at %s", self.uri)

    def close(self) -> None:
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed.")

    def __enter__(self) -> "Neo4jGraphLoader":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Retry wrapper
    # ------------------------------------------------------------------

    def _run_with_retry(self, work_fn, *args, **kwargs):
        attempt = 0
        while True:
            try:
                with self.driver.session(database=self.database) as session:
                    return session.execute_write(work_fn, *args, **kwargs)
            except (ServiceUnavailable, TransientError) as exc:
                attempt += 1
                if attempt > self.max_retries:
                    logger.error("Neo4j write failed after %s retries: %s", attempt - 1, exc)
                    raise
                sleep_for = self.retry_backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "Neo4j transient error (attempt %s/%s): %s — retrying in %.1fs",
                    attempt, self.max_retries, exc, sleep_for,
                )
                time.sleep(sleep_for)

    # ------------------------------------------------------------------
    # Schema setup
    # ------------------------------------------------------------------

    def create_constraints(self) -> None:
        def _create(tx):
            for label in VALID_ENTITY_LABELS:
                tx.run(
                    f"""
                    CREATE CONSTRAINT {label.lower()}_canonical_id_unique IF NOT EXISTS
                    FOR (n:{label}) REQUIRE n.canonical_id IS UNIQUE
                    """
                )

        self._run_with_retry(_create)
        logger.info("Constraints ensured for labels: %s", sorted(VALID_ENTITY_LABELS))

    # ------------------------------------------------------------------
    # Batched loads
    # ------------------------------------------------------------------

    @staticmethod
    def _chunked(items: List, size: int):
        for i in range(0, len(items), size):
            yield items[i : i + size]

    def load_entities(self, entities: List[ResolvedEntity]) -> int:
        by_label: Dict[str, List[ResolvedEntity]] = {}
        for e in entities:
            by_label.setdefault(e.label, []).append(e)

        total = 0
        for label, label_entities in by_label.items():
            if label not in VALID_ENTITY_LABELS:
                logger.warning(
                    "Skipping %s entities with unrecognized label %r", len(label_entities), label
                )
                continue

            for batch in self._chunked(label_entities, self.batch_size):
                rows = [
                    {
                        "canonical_id": e.canonical_id,
                        "name": e.name,
                        "aliases": e.aliases,
                        "mention_count": len(e.mentions),
                    }
                    for e in batch
                ]

                def _write(tx, rows=rows, label=label):
                    tx.run(
                        f"""
                        UNWIND $rows AS row
                        MERGE (n:{label} {{canonical_id: row.canonical_id}})
                        SET n.name = row.name,
                            n.aliases = row.aliases,
                            n.mention_count = row.mention_count
                        """,
                        rows=rows,
                    )

                self._run_with_retry(_write)
                total += len(batch)

        logger.info("Loaded %s entities in batches of <= %s.", total, self.batch_size)
        return total

    def load_relationships(self, relationships: List[CanonicalRelationship]) -> int:
        by_relation: Dict[str, List[CanonicalRelationship]] = {}
        for r in relationships:
            by_relation.setdefault(r.relation, []).append(r)

        total = 0
        for relation, rel_list in by_relation.items():
            if relation not in VALID_RELATIONS:
                logger.warning(
                    "Skipping %s relationships with unrecognized type %r", len(rel_list), relation
                )
                continue

            for batch in self._chunked(rel_list, self.batch_size):
                rows = [
                    {
                        "source": r.source,
                        "target": r.target,
                        "evidence_count": len(r.mentions),
                        "sources": [f"{m.document_id}#{m.chunk_id}" for m in r.mentions],
                    }
                    for r in batch
                ]

                def _write(tx, rows=rows, relation=relation):
                    tx.run(
                        f"""
                        UNWIND $rows AS row
                        MATCH (a {{canonical_id: row.source}})
                        MATCH (b {{canonical_id: row.target}})
                        MERGE (a)-[r:{relation}]->(b)
                        SET r.evidence_count = row.evidence_count,
                            r.sources = row.sources
                        """,
                        rows=rows,
                    )

                self._run_with_retry(_write)
                total += len(batch)

        logger.info("Loaded %s relationships in batches of <= %s.", total, self.batch_size)
        return total

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def count_nodes(self) -> int:
        with self.driver.session(database=self.database) as session:
            return session.run("MATCH (n) RETURN count(n) AS c").single()["c"]

    def count_relationships(self) -> int:
        with self.driver.session(database=self.database) as session:
            return session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]

    def verify_graph(self) -> Dict[str, int]:
        summary = {"nodes": self.count_nodes(), "relationships": self.count_relationships()}
        logger.info("Graph summary — nodes: %s, relationships: %s", summary["nodes"], summary["relationships"])
        return summary
