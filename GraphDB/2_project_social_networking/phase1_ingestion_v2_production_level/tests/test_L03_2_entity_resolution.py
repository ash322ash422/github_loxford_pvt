from L03_2_entity_resolution import EntityResolver
from schemas import ExtractedEntity, ExtractedRelationship, GraphDocument


def _graph(document_id, chunk_id, entities):
    return GraphDocument(document_id=document_id, chunk_id=chunk_id, entities=entities, relationships=[])


def test_identical_entities_across_documents_merge_into_one():
    doc1 = _graph("doc_1", 1, [ExtractedEntity(id="person_alice", name="Alice", label="Person")])
    doc2 = _graph("doc_2", 1, [ExtractedEntity(id="person_alice", name="Alice", label="Person")])

    resolved, alias_map = EntityResolver().resolve([doc1, doc2])

    assert len(resolved) == 1
    assert resolved[0].canonical_id == "person_alice"
    assert len(resolved[0].mentions) == 2
    assert {m.document_id for m in resolved[0].mentions} == {"doc_1", "doc_2"}


def test_spelling_variants_across_documents_are_merged():
    """This is the exact failure mode the original pipeline had: the same
    organization extracted as 'TechHub' in one document and 'Tech Hub' in
    another, with different LLM-assigned ids, must resolve to one node."""
    doc1 = _graph("doc_1", 1, [ExtractedEntity(id="organization_techhub", name="TechHub", label="Organization")])
    doc2 = _graph("doc_2", 1, [ExtractedEntity(id="organization_tech_hub", name="Tech Hub", label="Organization")])

    resolved, alias_map = EntityResolver().resolve([doc1, doc2])

    assert len(resolved) == 1
    entity = resolved[0]
    assert set(entity.aliases) >= {"organization_tech_hub", "Tech Hub"} or set(entity.aliases) >= {
        "organization_techhub", "TechHub"
    }
    # Both original local ids map to the same canonical id.
    assert alias_map[("doc_1", "organization_techhub")] == alias_map[("doc_2", "organization_tech_hub")]


def test_same_name_different_label_does_not_merge():
    doc1 = _graph("doc_1", 1, [ExtractedEntity(id="person_diana", name="Diana", label="Person")])
    doc2 = _graph("doc_2", 1, [ExtractedEntity(id="product_diana", name="Diana", label="Product")])

    resolved, _ = EntityResolver().resolve([doc1, doc2])

    assert len(resolved) == 2
    assert {e.label for e in resolved} == {"Person", "Product"}


def test_dissimilar_names_do_not_merge():
    doc1 = _graph("doc_1", 1, [ExtractedEntity(id="person_alice", name="Alice", label="Person")])
    doc2 = _graph("doc_2", 1, [ExtractedEntity(id="person_bob", name="Bob", label="Person")])

    resolved, alias_map = EntityResolver().resolve([doc1, doc2])

    assert len(resolved) == 2
    assert alias_map[("doc_1", "person_alice")] != alias_map[("doc_2", "person_bob")]


def test_alias_map_covers_every_local_id():
    doc1 = _graph("doc_1", 1, [
        ExtractedEntity(id="person_alice", name="Alice", label="Person"),
        ExtractedEntity(id="person_bob", name="Bob", label="Person"),
    ])
    resolved, alias_map = EntityResolver().resolve([doc1])

    assert ("doc_1", "person_alice") in alias_map
    assert ("doc_1", "person_bob") in alias_map


def test_resolution_clusters_multiple_name_variants_across_three_documents():
    """Three documents, three slightly different spellings of the same
    group, three different LLM-assigned ids -> should all collapse into
    a single canonical entity with all three ids/names recorded as aliases."""
    doc1 = _graph("doc_1", 1, [ExtractedEntity(id="group_dataclub", name="DataClub", label="Group")])
    doc2 = _graph("doc_2", 1, [ExtractedEntity(id="group_data_club", name="Data Club", label="Group")])
    doc3 = _graph("doc_3", 1, [ExtractedEntity(id="group_data_clubs", name="Data Clubs", label="Group")])

    resolved, alias_map = EntityResolver().resolve([doc1, doc2, doc3])

    canonical_ids = {
        alias_map[("doc_1", "group_dataclub")],
        alias_map[("doc_2", "group_data_club")],
        alias_map[("doc_3", "group_data_clubs")],
    }
    assert len(canonical_ids) == 1
    assert len(resolved) == 1
    assert len(resolved[0].mentions) == 3
