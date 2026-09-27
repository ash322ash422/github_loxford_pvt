"""
L03_2_entity_resolution.py

Stage 3b: Entity Resolution

Merges entities that refer to the same real-world thing across chunks
and *across documents*, even when the LLM assigned them slightly
different ids or name spellings. This is what the original pipeline was
missing — it only did exact-id-match dedup, which silently breaks the
moment the same entity is extracted with a different id in a different
document.

Approach (deliberately dependency-free — no embeddings, no LLM calls,
fully deterministic and unit-testable):

1. Blocking — partition candidates into small buckets (same label +
   same first characters of normalized name) so we never do an O(n^2)
   comparison across the whole corpus.
2. Scoring — within a bucket, score each pair with a name-similarity
   function (swappable via `similarity_fn` — plug in an embedding-based
   scorer later if name matching isn't precise enough for your corpus).
3. Clustering — union-find over scored pairs, so resolution is
   transitive (A~B, B~C => A~B~C) and independent of comparison order.

The output alias_map is keyed by (document_id, local_entity_id) because
the same local id string can mean different things in different
documents before resolution.
"""

from __future__ import annotations

import re
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Callable, Dict, List, Tuple

from schemas import GraphDocument, Mention, ResolvedEntity

DEFAULT_SIMILARITY_THRESHOLD = 0.86

AliasKey = Tuple[str, str]  # (document_id, local_entity_id)


def _normalize_name(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def _blocking_key(label: str, name: str) -> str:
    """Same label + first 3 chars of normalized name -> small candidate buckets."""
    norm = _normalize_name(name)
    prefix = norm[:3] if norm else ""
    return f"{label}::{prefix}"


def default_similarity(a: str, b: str) -> float:
    """Default scorer: normalized-name similarity ratio (0..1)."""
    return SequenceMatcher(None, _normalize_name(a), _normalize_name(b)).ratio()


class _UnionFind:
    """Minimal disjoint-set with path compression, deterministic tie-break."""

    def __init__(self) -> None:
        self.parent: Dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        # Deterministic so output doesn't depend on insertion/traversal order.
        if ra < rb:
            self.parent[rb] = ra
        else:
            self.parent[ra] = rb


class EntityResolver:
    def __init__(
        self,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        similarity_fn: Callable[[str, str], float] = default_similarity,
    ):
        self.similarity_threshold = similarity_threshold
        self.similarity_fn = similarity_fn

    def resolve(
        self, graph_documents: List[GraphDocument]
    ) -> Tuple[List[ResolvedEntity], Dict[AliasKey, str]]:
        """
        Returns
        -------
        resolved_entities : List[ResolvedEntity]
        alias_map : Dict[(document_id, local_id), canonical_id]
            Used by L03_3 to rewrite relationship source/target references.
        """

        records: List[Tuple[str, int, str, str, str]] = []
        # (document_id, chunk_id, local_id, name, label)
        for graph in graph_documents:
            for entity in graph.entities:
                records.append((graph.document_id, graph.chunk_id, entity.id, entity.name, entity.label))

        if not records:
            return [], {}

        def record_key(i: int) -> str:
            doc_id, _, local_id, _, _ = records[i]
            return f"{doc_id}::{local_id}"

        uf = _UnionFind()
        for i in range(len(records)):
            uf.find(record_key(i))

        buckets: Dict[str, List[int]] = defaultdict(list)
        for idx, (_, _, _, name, label) in enumerate(records):
            buckets[_blocking_key(label, name)].append(idx)

        for bucket_indices in buckets.values():
            for i in range(len(bucket_indices)):
                for j in range(i + 1, len(bucket_indices)):
                    idx_a, idx_b = bucket_indices[i], bucket_indices[j]
                    _, _, _, name_a, label_a = records[idx_a]
                    _, _, _, name_b, label_b = records[idx_b]
                    if label_a != label_b:
                        continue
                    if self.similarity_fn(name_a, name_b) >= self.similarity_threshold:
                        uf.union(record_key(idx_a), record_key(idx_b))

        clusters: Dict[str, List[int]] = defaultdict(list)
        for idx in range(len(records)):
            clusters[uf.find(record_key(idx))].append(idx)

        resolved_entities: List[ResolvedEntity] = []
        alias_map: Dict[AliasKey, str] = {}

        # Sort clusters for deterministic output ordering.
        for root in sorted(clusters.keys()):
            cluster_indices = clusters[root]
            cluster_records = [records[i] for i in cluster_indices]

            id_counts: Dict[str, int] = defaultdict(int)
            for _, _, local_id, _, _ in cluster_records:
                id_counts[local_id] += 1
            # Most frequent local id wins; alphabetical tie-break for determinism.
            canonical_id = max(sorted(id_counts.items()), key=lambda kv: kv[1])[0]

            label = cluster_records[0][4]
            canonical_name = max((rec[3] for rec in cluster_records), key=len)

            aliases = sorted(
                {local_id for _, _, local_id, _, _ in cluster_records if local_id != canonical_id}
                | {name for _, _, _, name, _ in cluster_records if name != canonical_name}
            )

            mentions = [
                Mention(document_id=doc_id, chunk_id=chunk_id, surface_form=name)
                for doc_id, chunk_id, _, name, _ in cluster_records
            ]

            resolved_entities.append(
                ResolvedEntity(
                    canonical_id=canonical_id,
                    name=canonical_name,
                    label=label,
                    aliases=aliases,
                    mentions=mentions,
                )
            )

            for doc_id, _, local_id, _, _ in cluster_records:
                alias_map[(doc_id, local_id)] = canonical_id

        return resolved_entities, alias_map
