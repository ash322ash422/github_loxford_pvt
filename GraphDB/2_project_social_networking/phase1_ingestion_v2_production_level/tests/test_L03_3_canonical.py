from L03_2_entity_resolution import EntityResolver
from L03_3_canonical import build_canonical_graph
from schemas import ExtractedEntity, ExtractedRelationship, GraphDocument


def _graph(document_id, chunk_id, entities=None, relationships=None):
    return GraphDocument(
        document_id=document_id, chunk_id=chunk_id,
        entities=entities or [], relationships=relationships or [],
    )


def test_relationships_are_rewritten_to_canonical_ids_and_merged_across_documents():
    doc1 = _graph(
        "doc_1", 1,
        entities=[
            ExtractedEntity(id="person_alice", name="Alice", label="Person"),
            ExtractedEntity(id="organization_techhub", name="TechHub", label="Organization"),
        ],
        relationships=[ExtractedRelationship(source="person_alice", target="organization_techhub", relation="CEO_OF")],
    )
    doc2 = _graph(
        "doc_2", 1,
        entities=[
            ExtractedEntity(id="person_alice", name="Alice", label="Person"),
            ExtractedEntity(id="organization_tech_hub", name="Tech Hub", label="Organization"),
        ],
        relationships=[ExtractedRelationship(source="person_alice", target="organization_tech_hub", relation="CEO_OF")],
    )

    resolved, alias_map = EntityResolver().resolve([doc1, doc2])
    canonical = build_canonical_graph([doc1, doc2], resolved, alias_map)

    # Same fact seen in both documents -> one relationship, two pieces of evidence.
    assert len(canonical.relationships) == 1
    rel = canonical.relationships[0]
    assert rel.evidence_count == 2
    assert {m.document_id for m in rel.mentions} == {"doc_1", "doc_2"}


def test_symmetric_relationships_collapse_regardless_of_direction():
    doc = _graph(
        "doc_1", 1,
        entities=[
            ExtractedEntity(id="person_bob", name="Bob", label="Person"),
            ExtractedEntity(id="person_charlie", name="Charlie", label="Person"),
        ],
        relationships=[
            ExtractedRelationship(source="person_bob", target="person_charlie", relation="MARRIED_TO"),
            ExtractedRelationship(source="person_charlie", target="person_bob", relation="MARRIED_TO"),
        ],
    )
    resolved, alias_map = EntityResolver().resolve([doc])
    canonical = build_canonical_graph([doc], resolved, alias_map)

    married_rels = [r for r in canonical.relationships if r.relation == "MARRIED_TO"]
    assert len(married_rels) == 1
    assert married_rels[0].evidence_count == 2


def test_relationship_dropped_if_endpoint_entity_was_filtered_out():
    doc = _graph(
        "doc_1", 1,
        entities=[ExtractedEntity(id="person_alice", name="Alice", label="Person")],
        # relationship references an entity id that never appears in `entities`
        relationships=[ExtractedRelationship(source="person_alice", target="person_ghost", relation="MANAGES")],
    )
    resolved, alias_map = EntityResolver().resolve([doc])
    canonical = build_canonical_graph([doc], resolved, alias_map)

    assert canonical.relationships == []


def test_non_symmetric_relationships_with_different_directions_stay_separate():
    doc = _graph(
        "doc_1", 1,
        entities=[
            ExtractedEntity(id="person_alice", name="Alice", label="Person"),
            ExtractedEntity(id="person_bob", name="Bob", label="Person"),
        ],
        relationships=[
            ExtractedRelationship(source="person_alice", target="person_bob", relation="MANAGES"),
            ExtractedRelationship(source="person_bob", target="person_alice", relation="MANAGES"),
        ],
    )
    resolved, alias_map = EntityResolver().resolve([doc])
    canonical = build_canonical_graph([doc], resolved, alias_map)

    # MANAGES is not symmetric -> both directions are legitimate, distinct edges.
    assert len(canonical.relationships) == 2
