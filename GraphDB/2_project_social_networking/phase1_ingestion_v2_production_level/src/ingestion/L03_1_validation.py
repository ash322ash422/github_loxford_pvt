"""
L03_1_validation.py

Stage 3a: Validation & Normalization

Cleans up raw per-chunk extraction output before entity resolution runs:
drops invalid labels/relations, normalizes id formatting, filters
generic/non-specific entities, and removes now-orphaned relationships.

Operates on a flat list of `GraphDocument`s spanning any number of
source documents — nothing here is document-count-aware, which is what
makes it safe to call once on an entire multi-document corpus.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import List

from schemas import (
    GENERIC_ENTITY_NAMES,
    VALID_ENTITY_LABELS,
    VALID_RELATIONS,
    GraphDocument,
)


class GraphValidator:
    """Performs validation and normalization of a list of GraphDocuments."""

    def __init__(self, graph_documents: List[GraphDocument]):
        self.graph_documents = deepcopy(graph_documents)

    # Rule 1
    def validate_entity_labels(self) -> "GraphValidator":
        """Remove entities having invalid labels."""
        for graph in self.graph_documents:
            graph.entities = [e for e in graph.entities if e.label in VALID_ENTITY_LABELS]
        return self

    # Rule 2
    def remove_generic_entities(self) -> "GraphValidator":
        """
        Remove entities that are generic/non-specific references rather
        than named things (e.g. "the team", "staff").
        """
        for graph in self.graph_documents:
            graph.entities = [
                e for e in graph.entities
                if e.name.strip().lower() not in GENERIC_ENTITY_NAMES
            ]
        return self

    # Rule 3
    def normalize_entity_ids(self) -> "GraphValidator":
        """
        Normalize entity ids.

        Example: "Person.Alice" / "Person Alice" / "person-alice" -> "person_alice"
        """
        for graph in self.graph_documents:
            for entity in graph.entities:
                entity.id = self._normalize_id(entity.id)
        for graph in self.graph_documents:
            for rel in graph.relationships:
                rel.source = self._normalize_id(rel.source)
                rel.target = self._normalize_id(rel.target)
        return self

    # Rule 4
    def remove_duplicate_entities_within_chunk(self) -> "GraphValidator":
        """
        Remove duplicate entities *within a single chunk* (same normalized
        id extracted twice by the LLM in one call). Cross-chunk/cross-document
        duplicates are intentionally left for entity resolution (L03_2) to
        handle, since that stage needs every mention to build provenance.
        """
        for graph in self.graph_documents:
            seen = set()
            deduped = []
            for entity in graph.entities:
                if entity.id not in seen:
                    seen.add(entity.id)
                    deduped.append(entity)
            graph.entities = deduped
        return self

    @staticmethod
    def _normalize_id(entity_id: str) -> str:
        entity_id = entity_id.lower()
        entity_id = entity_id.replace(".", "_")
        entity_id = entity_id.replace("-", "_")
        entity_id = entity_id.replace(" ", "_")
        entity_id = re.sub(r"_+", "_", entity_id)
        return entity_id

    # Rule 5
    def validate_relationship_types(self) -> "GraphValidator":
        """Remove relationships having invalid relation names."""
        for graph in self.graph_documents:
            graph.relationships = [r for r in graph.relationships if r.relation in VALID_RELATIONS]
        return self

    # Rule 6
    def remove_duplicate_relationships_within_chunk(self) -> "GraphValidator":
        """Remove duplicate (source, target, relation) triples within a single chunk."""
        for graph in self.graph_documents:
            seen = set()
            deduped = []
            for rel in graph.relationships:
                key = (rel.source, rel.target, rel.relation)
                if key not in seen:
                    seen.add(key)
                    deduped.append(rel)
            graph.relationships = deduped
        return self

    # Rule 7
    def remove_orphan_relationships(self) -> "GraphValidator":
        """Remove relationships whose source or target entity doesn't exist in that chunk."""
        for graph in self.graph_documents:
            entity_ids = {e.id for e in graph.entities}
            graph.relationships = [
                r for r in graph.relationships
                if r.source in entity_ids and r.target in entity_ids
            ]
        return self

    def validate(self) -> "GraphValidator":
        """Run the complete validation pipeline."""
        return (
            self
            .validate_entity_labels()
            .remove_generic_entities()
            .normalize_entity_ids()
            .remove_duplicate_entities_within_chunk()
            .validate_relationship_types()
            .remove_duplicate_relationships_within_chunk()
            .remove_orphan_relationships()
        )

    def get_graph_documents(self) -> List[GraphDocument]:
        return self.graph_documents
