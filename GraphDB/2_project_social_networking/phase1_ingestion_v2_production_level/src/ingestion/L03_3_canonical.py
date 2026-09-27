"""
L03_3_canonical.py

Stage 3c: Canonicalization

Combines resolved entities (L03_2) with the raw per-chunk relationships
to build the final `CanonicalGraph` — the artifact loaded into Neo4j
(L04). This is the one place relationship identity is decided:

* Relationship endpoints are rewritten from local (per-document) ids to
  global canonical ids using the entity-resolution alias map.
* Relationships are merged by (source, target, relation) — for
  relations known to be symmetric (MARRIED_TO, etc.), source/target are
  sorted first so "A MARRIED_TO B" and "B MARRIED_TO A" collapse into
  one edge instead of two.
* Every distinct chunk/document that supports a relationship survives
  as a `Mention`, so `evidence_count` and full provenance are available
  downstream (e.g. for citing why an edge exists during retrieval).
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from schemas import (
    CanonicalGraph,
    CanonicalRelationship,
    GraphDocument,
    Mention,
    ResolvedEntity,
    SYMMETRIC_RELATIONS,
)

RelKey = Tuple[str, str, str]


def _relationship_key(source: str, target: str, relation: str) -> RelKey:
    if relation in SYMMETRIC_RELATIONS:
        source, target = sorted([source, target])
    return (source, target, relation)


def build_canonical_graph(
    graph_documents: List[GraphDocument],
    resolved_entities: List[ResolvedEntity],
    alias_map: Dict[Tuple[str, str], str],
) -> CanonicalGraph:

    canonical_entity_ids = {e.canonical_id for e in resolved_entities}
    relationship_map: Dict[RelKey, CanonicalRelationship] = {}

    dropped_orphan_count = 0

    for graph in graph_documents:
        for rel in graph.relationships:
            source_canonical = alias_map.get((graph.document_id, rel.source))
            target_canonical = alias_map.get((graph.document_id, rel.target))

            if (
                not source_canonical
                or not target_canonical
                or source_canonical not in canonical_entity_ids
                or target_canonical not in canonical_entity_ids
            ):
                dropped_orphan_count += 1
                continue

            key = _relationship_key(source_canonical, target_canonical, rel.relation)
            mention = Mention(
                document_id=graph.document_id,
                chunk_id=graph.chunk_id,
                surface_form=rel.relation,
            )

            if key in relationship_map:
                relationship_map[key].mentions.append(mention)
            else:
                # Preserve the canonical (possibly sorted) source/target from
                # the key so symmetric relations always point the same way.
                key_source, key_target, key_relation = key
                relationship_map[key] = CanonicalRelationship(
                    source=key_source,
                    target=key_target,
                    relation=key_relation,
                    mentions=[mention],
                )

    return CanonicalGraph(
        entities=resolved_entities,
        relationships=list(relationship_map.values()),
    )
