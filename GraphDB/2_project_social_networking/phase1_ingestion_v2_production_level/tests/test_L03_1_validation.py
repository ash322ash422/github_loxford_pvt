from L03_1_validation import GraphValidator
from schemas import ExtractedEntity, ExtractedRelationship, GraphDocument


def _graph(document_id="doc_1", chunk_id=1, entities=None, relationships=None):
    return GraphDocument(
        document_id=document_id,
        chunk_id=chunk_id,
        entities=entities or [],
        relationships=relationships or [],
    )


def test_invalid_entity_labels_are_removed():
    graph = _graph(entities=[
        ExtractedEntity(id="person_alice", name="Alice", label="Person"),
        ExtractedEntity(id="thing_x", name="X", label="NotARealLabel"),
    ])
    result = GraphValidator([graph]).validate_entity_labels().get_graph_documents()
    assert [e.id for e in result[0].entities] == ["person_alice"]


def test_generic_entities_are_removed():
    graph = _graph(entities=[
        ExtractedEntity(id="person_alice", name="Alice", label="Person"),
        ExtractedEntity(id="group_team", name="team", label="Group"),
        ExtractedEntity(id="group_staff", name="Staff", label="Group"),
    ])
    result = GraphValidator([graph]).remove_generic_entities().get_graph_documents()
    names = {e.name for e in result[0].entities}
    assert names == {"Alice"}


def test_entity_ids_are_normalized():
    graph = _graph(entities=[ExtractedEntity(id="Person.Alice Smith", name="Alice", label="Person")])
    result = GraphValidator([graph]).normalize_entity_ids().get_graph_documents()
    assert result[0].entities[0].id == "person_alice_smith"


def test_relationship_endpoints_are_normalized_too():
    graph = _graph(
        entities=[ExtractedEntity(id="Person.Alice", name="Alice", label="Person")],
        relationships=[ExtractedRelationship(source="Person.Alice", target="Org.TechHub", relation="WORKS_AT")],
    )
    result = GraphValidator([graph]).normalize_entity_ids().get_graph_documents()
    rel = result[0].relationships[0]
    assert rel.source == "person_alice"
    assert rel.target == "org_techhub"


def test_invalid_relations_are_removed():
    graph = _graph(
        entities=[
            ExtractedEntity(id="person_alice", name="Alice", label="Person"),
            ExtractedEntity(id="person_bob", name="Bob", label="Person"),
        ],
        relationships=[
            ExtractedRelationship(source="person_alice", target="person_bob", relation="WORKS_AT"),
            ExtractedRelationship(source="person_alice", target="person_bob", relation="TOTALLY_MADE_UP"),
        ],
    )
    result = GraphValidator([graph]).validate_relationship_types().get_graph_documents()
    assert [r.relation for r in result[0].relationships] == ["WORKS_AT"]


def test_orphan_relationships_are_removed_after_entity_filtering():
    graph = _graph(
        entities=[ExtractedEntity(id="person_alice", name="Alice", label="Person")],
        relationships=[
            ExtractedRelationship(source="person_alice", target="person_bob", relation="MANAGES"),
        ],
    )
    result = (
        GraphValidator([graph])
        .remove_orphan_relationships()
        .get_graph_documents()
    )
    # person_bob doesn't exist as an entity in this chunk -> relationship dropped
    assert result[0].relationships == []


def test_full_validate_pipeline_end_to_end():
    graph = _graph(
        entities=[
            ExtractedEntity(id="Person.Alice", name="Alice", label="Person"),
            ExtractedEntity(id="group_team", name="the team", label="Group"),
            ExtractedEntity(id="thing_x", name="X", label="BadLabel"),
        ],
        relationships=[
            ExtractedRelationship(source="Person.Alice", target="group_team", relation="MEMBER_OF"),
            ExtractedRelationship(source="Person.Alice", target="thing_x", relation="MADE_UP_RELATION"),
        ],
    )
    result = GraphValidator([graph]).validate().get_graph_documents()

    assert [e.id for e in result[0].entities] == ["person_alice"]
    # relationship to the now-removed "the team" entity should be dropped as orphaned
    assert result[0].relationships == []
