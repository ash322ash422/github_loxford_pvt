import pytest

from L02_extraction import extract_corpus, extract_graph, load_graph_documents, save_graph_documents
from schemas import ExtractedEntity, ExtractedRelationship, ExtractionResult, GraphDocument


class FakeChain:
    """Stands in for the real LangChain runnable so no network/API key is needed."""

    def __init__(self, responses=None, fail_times=0, exception=RuntimeError("boom")):
        self.responses = responses or []
        self.calls = 0
        self.fail_times = fail_times
        self.exception = exception

    def invoke(self, _input):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise self.exception
        return self.responses[(self.calls - self.fail_times - 1) % len(self.responses)]


SAMPLE_RESULT = ExtractionResult(
    entities=[ExtractedEntity(id="person_alice", name="Alice", label="Person")],
    relationships=[],
)


def _chunk(document_id="doc_1", chunk_id=1, text="Alice works here."):
    return {"document_id": document_id, "chunk_id": chunk_id, "text": text}


def test_extract_graph_tags_document_and_chunk_id():
    chain = FakeChain(responses=[SAMPLE_RESULT])
    graph = extract_graph(_chunk(document_id="doc_x", chunk_id=7), chain=chain)

    assert graph.document_id == "doc_x"
    assert graph.chunk_id == 7
    assert graph.entities[0].name == "Alice"


def test_extract_graph_retries_transient_failures(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _seconds: None)  # don't actually wait in tests

    chain = FakeChain(responses=[SAMPLE_RESULT], fail_times=2)
    graph = extract_graph(_chunk(), chain=chain, max_retries=3, retry_backoff_seconds=0.01)

    assert chain.calls == 3
    assert graph.entities[0].name == "Alice"


def test_extract_graph_raises_after_exhausting_retries(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _seconds: None)

    chain = FakeChain(responses=[SAMPLE_RESULT], fail_times=10)
    with pytest.raises(RuntimeError):
        extract_graph(_chunk(), chain=chain, max_retries=2, retry_backoff_seconds=0.01)


def test_extract_corpus_isolates_failures_and_keeps_going(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _seconds: None)

    good_chunk = _chunk(document_id="doc_1", chunk_id=1, text="Alice works here.")
    bad_chunk = _chunk(document_id="doc_1", chunk_id=2, text="POISON_CHUNK")
    another_good_chunk = _chunk(document_id="doc_2", chunk_id=1, text="Bob works there.")

    class PermanentlyFailsOnMarkerChain:
        """Fails every single call for the 'poisoned' chunk, regardless of
        retry count, so we can prove the failure is permanent (not just
        transient) and correctly ends up in the dead-letter list."""

        def invoke(self, input_):
            if input_["text"] == "POISON_CHUNK":
                raise RuntimeError("simulated permanent extraction failure")
            return SAMPLE_RESULT

    chain = PermanentlyFailsOnMarkerChain()
    graphs, failures = extract_corpus(
        [good_chunk, bad_chunk, another_good_chunk], chain=chain
    )

    # bad_chunk fails all retries (default max_retries=3) -> 1 failure recorded,
    # the other two chunks still succeed.
    assert len(failures) == 1
    assert failures[0]["chunk_id"] == 2
    assert len(graphs) == 2
    assert {g.document_id for g in graphs} == {"doc_1", "doc_2"}


def test_save_and_load_graph_documents_round_trip(tmp_path):
    graphs = [
        GraphDocument(
            document_id="doc_1", chunk_id=1,
            entities=[ExtractedEntity(id="person_alice", name="Alice", label="Person")],
            relationships=[],
        )
    ]
    path = tmp_path / "cache" / "extracted.json"  # nested dir must be created automatically

    save_graph_documents(graphs, path)
    assert path.exists()

    loaded = load_graph_documents(path)
    assert loaded == graphs


def test_extract_corpus_writes_cache_file_when_cache_path_given(tmp_path):
    cache_path = tmp_path / "L02_extracted_graph_documents.json"
    chain = FakeChain(responses=[SAMPLE_RESULT])

    graphs, failures = extract_corpus([_chunk()], chain=chain, cache_path=cache_path)

    assert cache_path.exists()
    assert failures == []
    assert chain.calls == 1


def test_extract_corpus_uses_cache_and_never_calls_the_llm_again(tmp_path):
    cache_path = tmp_path / "L02_extracted_graph_documents.json"
    chain = FakeChain(responses=[SAMPLE_RESULT])

    # First run: cache miss, LLM is called, result written to disk.
    extract_corpus([_chunk()], chain=chain, cache_path=cache_path)
    assert chain.calls == 1

    # Second run: cache hit — chain must NOT be called again.
    class ExplodingChain:
        def invoke(self, _input):
            raise AssertionError("LLM should not be called on a cache hit")

    graphs, failures = extract_corpus([_chunk()], chain=ExplodingChain(), cache_path=cache_path)

    assert failures == []
    assert graphs[0].entities[0].name == "Alice"


def test_extract_corpus_use_cache_false_forces_reextraction(tmp_path):
    cache_path = tmp_path / "L02_extracted_graph_documents.json"
    chain = FakeChain(responses=[SAMPLE_RESULT])

    extract_corpus([_chunk()], chain=chain, cache_path=cache_path)
    assert chain.calls == 1

    # use_cache=False must force a real re-extraction even though the file exists.
    extract_corpus([_chunk()], chain=chain, cache_path=cache_path, use_cache=False)
    assert chain.calls == 2
