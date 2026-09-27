"""
schemas.py

Shared Pydantic data contracts for the ingestion pipeline.

Two families of models:

* Extraction-time models (`ExtractedEntity`, `ExtractedRelationship`,
  `ExtractionResult`, `GraphDocument`) — per-chunk, per-document output
  straight from the LLM. No cross-document identity guarantees: the same
  real-world entity may appear under different `id`s in different chunks.

* Resolved models (`ResolvedEntity`, `CanonicalRelationship`,
  `CanonicalGraph`) — de-duplicated across the whole corpus by entity
  resolution (L03_2), carrying `Mention` provenance back to the exact
  document/chunk each fact came from.
"""

from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field

VALID_ENTITY_LABELS = {"Person", "Organization", "Product", "Platform", "Group"}

VALID_RELATIONS = {
    "CEO_OF",
    "MANAGES",
    "DEVELOPED",
    "WORKS_AT",
    "WORKS_ON",
    "MARRIED_TO",
    "SHARES_OFFICE_WITH",
    "MEMBER_OF",
    "ORGANIZES",
    "CO_ORGANIZES_WITH",
    "INTERACTS_WITH",
    "FOLLOWS",
    "USES_PLATFORM",
    "MAINTAINS_PROFILE_ON",
    "VIEWS_POSTS",
    "REPORTS_TO",
}

SYMMETRIC_RELATIONS = {
    "MARRIED_TO",
    "SHARES_OFFICE_WITH",
    "CO_ORGANIZES_WITH",
    "INTERACTS_WITH",
}

# Generic/non-specific nouns the LLM sometimes mistakes for named entities
# (e.g. "the team", "the company") — filtered out during validation.
GENERIC_ENTITY_NAMES = {
    "team",
    "the team",
    "group",
    "company",
    "the company",
    "organization",
    "staff",
    "employees",
}


# ---------------------------------------------------------------------------
# Extraction-time models
# ---------------------------------------------------------------------------

class ExtractedEntity(BaseModel):
    """A single entity as extracted from one chunk by the LLM."""

    id: str = Field(description="LLM-assigned entity id, e.g. person_alice")
    name: str = Field(description="Entity name as it appeared in the text.")
    label: str = Field(description="Entity type: Person, Organization, Product, Platform, Group.")


class ExtractedRelationship(BaseModel):
    """A single relationship as extracted from one chunk by the LLM."""

    source: str = Field(description="Source entity id.")
    target: str = Field(description="Target entity id.")
    relation: str = Field(description="Relationship type, e.g. WORKS_AT.")


class ExtractionResult(BaseModel):
    """
    Raw shape the LLM is asked to produce for a single chunk. Kept
    separate from `GraphDocument` because `document_id`/`chunk_id` are
    known to the pipeline, not something the model should have to invent.
    """

    entities: List[ExtractedEntity] = Field(default_factory=list)
    relationships: List[ExtractedRelationship] = Field(default_factory=list)


class GraphDocument(BaseModel):
    """One chunk's worth of extracted entities/relationships, with provenance."""

    document_id: str = Field(description="Stable id of the source document.")
    chunk_id: int = Field(description="Chunk index within that document.")
    entities: List[ExtractedEntity] = Field(default_factory=list)
    relationships: List[ExtractedRelationship] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Resolved / canonical models
# ---------------------------------------------------------------------------

class Mention(BaseModel):
    """Provenance record: exactly where a fact was observed."""

    document_id: str
    chunk_id: int
    surface_form: str = Field(description="The name/relation string as it appeared in this mention.")


class ResolvedEntity(BaseModel):
    """An entity after cross-corpus entity resolution."""

    canonical_id: str
    name: str
    label: str
    aliases: List[str] = Field(default_factory=list, description="Other ids/names merged into this entity.")
    mentions: List[Mention] = Field(default_factory=list)


class CanonicalRelationship(BaseModel):
    """A relationship after cross-corpus de-duplication, with evidence."""

    source: str
    target: str
    relation: str
    mentions: List[Mention] = Field(default_factory=list)

    @property
    def evidence_count(self) -> int:
        return len(self.mentions)


class CanonicalGraph(BaseModel):
    """Final, de-duplicated graph ready for loading into Neo4j."""

    entities: List[ResolvedEntity] = Field(default_factory=list)
    relationships: List[CanonicalRelationship] = Field(default_factory=list)
