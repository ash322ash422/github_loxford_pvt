from unittest.mock import MagicMock

import pytest
from neo4j.exceptions import ServiceUnavailable

from L04_neo4j_loader import Neo4jGraphLoader
from schemas import CanonicalRelationship, Mention, ResolvedEntity


def _entity(canonical_id, name, label="Person"):
    return ResolvedEntity(
        canonical_id=canonical_id, name=name, label=label,
        aliases=[], mentions=[Mention(document_id="doc_1", chunk_id=1, surface_form=name)],
    )


def _rel(source, target, relation):
    return CanonicalRelationship(
        source=source, target=target, relation=relation,
        mentions=[Mention(document_id="doc_1", chunk_id=1, surface_form=relation)],
    )


@pytest.fixture
def loader():
    """A loader with a mocked driver — no real Neo4j instance required."""
    loader = Neo4jGraphLoader(
        uri="bolt://fake", username="fake", password="fake",
        batch_size=2, max_retries=2, retry_backoff_seconds=0.0,
    )
    loader.driver = MagicMock()
    return loader


def test_load_entities_batches_by_size(loader, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _s: None)

    entities = [_entity(f"person_{i}", f"Person {i}") for i in range(5)]

    write_calls = []

    def fake_run_with_retry(work_fn, *args, **kwargs):
        session = MagicMock()
        work_fn(session, *args, **kwargs)
        write_calls.append(session.run.call_args.kwargs["rows"])

    loader._run_with_retry = fake_run_with_retry
    total = loader.load_entities(entities)

    assert total == 5
    # batch_size=2 -> batches of [2, 2, 1]
    assert [len(batch) for batch in write_calls] == [2, 2, 1]


def test_load_entities_skips_unrecognized_labels(loader, caplog):
    entities = [_entity("thing_1", "Thing", label="NotARealLabel")]

    write_calls = []
    loader._run_with_retry = lambda work_fn, *a, **k: write_calls.append(1)

    total = loader.load_entities(entities)

    assert total == 0
    assert write_calls == []


def test_load_relationships_skips_unrecognized_relation_types(loader):
    rels = [_rel("person_a", "person_b", "TOTALLY_MADE_UP")]

    write_calls = []
    loader._run_with_retry = lambda work_fn, *a, **k: write_calls.append(1)

    total = loader.load_relationships(rels)

    assert total == 0
    assert write_calls == []


def test_run_with_retry_retries_transient_errors_then_succeeds(loader, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _s: None)

    attempts = {"count": 0}
    session_cm = MagicMock()

    def flaky_execute_write(work_fn, *args, **kwargs):
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise ServiceUnavailable("simulated outage")
        return "ok"

    session_cm.__enter__.return_value.execute_write.side_effect = flaky_execute_write
    loader.driver.session.return_value = session_cm

    result = loader._run_with_retry(lambda tx: None)

    assert result == "ok"
    assert attempts["count"] == 2


def test_run_with_retry_raises_after_exhausting_retries(loader, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _s: None)

    session_cm = MagicMock()
    session_cm.__enter__.return_value.execute_write.side_effect = ServiceUnavailable("still down")
    loader.driver.session.return_value = session_cm

    with pytest.raises(ServiceUnavailable):
        loader._run_with_retry(lambda tx: None)


def test_create_constraints_issues_one_statement_per_valid_label(loader):
    session_cm = MagicMock()
    loader.driver.session.return_value = session_cm

    # Bypass retry wrapper's own session handling and just call the real one,
    # but with the mocked driver already in place.
    loader.create_constraints()

    tx = session_cm.__enter__.return_value.execute_write.call_args[0][0]
    # `tx` here is the `_create` closure; verify it runs one statement per label
    # by invoking it directly against a mock transaction.
    mock_tx = MagicMock()
    tx(mock_tx)
    from schemas import VALID_ENTITY_LABELS
    assert mock_tx.run.call_count == len(VALID_ENTITY_LABELS)
