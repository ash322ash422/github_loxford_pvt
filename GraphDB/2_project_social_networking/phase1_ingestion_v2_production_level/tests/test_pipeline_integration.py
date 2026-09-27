"""
test_pipeline_integration.py

End-to-end test of L01 -> L02 -> L03_1 -> L03_2 -> L03_3, run against two
tiny synthetic documents, with a fake (canned) extraction chain standing
in for the real OpenAI call. Proves the multi-document wiring — and in
particular cross-document entity resolution — works together, without
needing network access or an API key.
"""

import json

from pipeline import run_pipeline
from schemas import ExtractedEntity, ExtractedRelationship, ExtractionResult


class CannedChain:
    """
    Returns a fixed ExtractionResult per chunk text, keyed by a substring
    match. This stands in for the real LLM so the integration test is
    deterministic and network-free.
    """

    def __init__(self, script):
        self.script = script  # list of (substring, ExtractionResult)

    def invoke(self, input_):
        text = input_["text"]
        for substring, result in self.script:
            if substring in text:
                return result
        raise AssertionError(f"CannedChain has no scripted response for: {text!r}")


def test_two_documents_with_spelling_variant_resolve_to_one_entity(tmp_path):
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "output"
    raw_dir.mkdir()

    (raw_dir / "doc_001.txt").write_text("TechHub is led by Alice.", encoding="utf-8")
    (raw_dir / "doc_002.txt").write_text("Tech Hub recently hired Bob.", encoding="utf-8")

    chain = CannedChain(
        [
            (
                "TechHub is led by Alice",
                ExtractionResult(
                    entities=[
                        ExtractedEntity(id="organization_techhub", name="TechHub", label="Organization"),
                        ExtractedEntity(id="person_alice", name="Alice", label="Person"),
                    ],
                    relationships=[
                        ExtractedRelationship(source="person_alice", target="organization_techhub", relation="CEO_OF"),
                    ],
                ),
            ),
            (
                "Tech Hub recently hired Bob",
                ExtractionResult(
                    entities=[
                        ExtractedEntity(id="organization_tech_hub", name="Tech Hub", label="Organization"),
                        ExtractedEntity(id="person_bob", name="Bob", label="Person"),
                    ],
                    relationships=[
                        ExtractedRelationship(source="person_bob", target="organization_tech_hub", relation="WORKS_AT"),
                    ],
                ),
            ),
        ]
    )

    graph = run_pipeline(raw_dir=raw_dir, output_dir=output_dir, extraction_chain=chain)

    org_entities = [e for e in graph.entities if e.label == "Organization"]
    assert len(org_entities) == 1, "TechHub / Tech Hub across two documents should resolve to one entity"
    assert len(org_entities[0].mentions) == 2

    person_names = {e.name for e in graph.entities if e.label == "Person"}
    assert person_names == {"Alice", "Bob"}

    assert len(graph.relationships) == 2

    # Output artifacts were actually written for inspection/debugging.
    assert (output_dir / "L02_extracted_graph_documents.json").exists()
    assert (output_dir / "L03_validated_graph.json").exists()
    assert (output_dir / "L03_canonical_graph.json").exists()

    canonical_on_disk = json.loads((output_dir / "L03_canonical_graph.json").read_text())
    assert len(canonical_on_disk["entities"]) == 3  # TechHub(merged), Alice, Bob


def test_second_pipeline_run_reuses_cached_extraction_without_calling_llm(tmp_path):
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "output"
    raw_dir.mkdir()
    (raw_dir / "doc_001.txt").write_text("TechHub is led by Alice.", encoding="utf-8")

    chain = CannedChain([
        (
            "TechHub is led by Alice",
            ExtractionResult(
                entities=[
                    ExtractedEntity(id="organization_techhub", name="TechHub", label="Organization"),
                    ExtractedEntity(id="person_alice", name="Alice", label="Person"),
                ],
                relationships=[
                    ExtractedRelationship(source="person_alice", target="organization_techhub", relation="CEO_OF"),
                ],
            ),
        ),
    ])

    first = run_pipeline(raw_dir=raw_dir, output_dir=output_dir, extraction_chain=chain)

    class ExplodingChain:
        def invoke(self, _input):
            raise AssertionError("LLM should not be called on the second run — cache should be used")

    second = run_pipeline(raw_dir=raw_dir, output_dir=output_dir, extraction_chain=ExplodingChain())

    assert len(second.entities) == len(first.entities)
    assert len(second.relationships) == len(first.relationships)


def test_refresh_extraction_forces_llm_call_even_with_cache_present(tmp_path):
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "output"
    raw_dir.mkdir()
    (raw_dir / "doc_001.txt").write_text("TechHub is led by Alice.", encoding="utf-8")

    result = ExtractionResult(
        entities=[ExtractedEntity(id="organization_techhub", name="TechHub", label="Organization")],
        relationships=[],
    )
    chain = CannedChain([("TechHub is led by Alice", result)])

    run_pipeline(raw_dir=raw_dir, output_dir=output_dir, extraction_chain=chain)

    calls = {"count": 0}

    class CountingChain:
        def invoke(self, _input):
            calls["count"] += 1
            return result

    run_pipeline(
        raw_dir=raw_dir, output_dir=output_dir, extraction_chain=CountingChain(),
        use_extraction_cache=False,
    )
    assert calls["count"] > 0


def test_pipeline_raises_clear_error_when_no_documents_found(tmp_path):
    raw_dir = tmp_path / "empty_raw"
    raw_dir.mkdir()
    output_dir = tmp_path / "output"

    import pytest
    with pytest.raises(FileNotFoundError):
        run_pipeline(raw_dir=raw_dir, output_dir=output_dir, extraction_chain=CannedChain([]))
