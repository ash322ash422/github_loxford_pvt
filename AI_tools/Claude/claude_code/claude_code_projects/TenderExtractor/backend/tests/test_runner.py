"""
Integration-level test for run_pipeline()'s tender pre-check gate: a
document that doesn't match any tender keyword in its first pages must stop
the pipeline early - status NOT_A_TENDER, no failed_stage, no consolidated
Excel produced - rather than running (and paying for) full OCR and LLM
extraction on something that was never a tender to begin with.

Azure calls (document_intelligence) are monkeypatched, so this never
touches real services.
"""
import pytest

from app import config
from app.pipeline.context import job_upload_path
from app.pipeline.runner import run_pipeline
from app.services import document_intelligence, job_db_backup, job_store

PDF_BYTES = b"%PDF-1.4 fake pdf bytes"


@pytest.fixture(autouse=True)
def isolated_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_UPLOAD_DIR", tmp_path / "data_uploads")
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(config, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(config, "JOBS_DB", tmp_path / "jobs.db")
    monkeypatch.setattr(config, "AZURE_STORAGE_CONNECTION_STRING", None)


def _seed_upload(blob_name: str, job_id: str) -> None:
    path = job_upload_path(job_id, blob_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(PDF_BYTES)


def test_non_tender_document_stops_early_with_no_output(monkeypatch):
    monkeypatch.setattr(document_intelligence, "validate_pdf_is_digital", lambda pdf_bytes: True)
    monkeypatch.setattr(document_intelligence, "analyze_document_from_bytes", lambda **kwargs: object())
    monkeypatch.setattr(
        document_intelligence, "extract_document_data",
        lambda result: {"pages": [{"page_number": 1, "text": "Dear Sir, please find our quarterly report."}]},
    )

    job_id = job_store.new_job_id()
    _seed_upload("plain.pdf", job_id)

    ctx = run_pipeline("plain.pdf", job_id=job_id)

    assert ctx.status == "NOT_A_TENDER"
    assert ctx.is_tender is False
    assert not ctx.consolidated_excel_path.exists()

    job = job_store.get_job(job_id)
    assert job["status"] == "NOT_A_TENDER"
    assert job["failed_stage"] is None


def test_job_db_pushed_after_not_a_tender_run(monkeypatch):
    monkeypatch.setattr(document_intelligence, "validate_pdf_is_digital", lambda pdf_bytes: True)
    monkeypatch.setattr(document_intelligence, "analyze_document_from_bytes", lambda **kwargs: object())
    monkeypatch.setattr(
        document_intelligence, "extract_document_data",
        lambda result: {"pages": [{"page_number": 1, "text": "no keywords here"}]},
    )
    calls = []
    monkeypatch.setattr(job_db_backup, "push_job_db_to_blob", lambda: calls.append(1))

    job_id = job_store.new_job_id()
    _seed_upload("plain.pdf", job_id)
    run_pipeline("plain.pdf", job_id=job_id)

    assert calls == [1]


def test_job_db_pushed_even_when_a_stage_fails(monkeypatch):
    monkeypatch.setattr(document_intelligence, "validate_pdf_is_digital", lambda pdf_bytes: True)

    def _broken_analyze(**kwargs):
        raise RuntimeError("Document Intelligence is down")

    monkeypatch.setattr(document_intelligence, "analyze_document_from_bytes", _broken_analyze)
    calls = []
    monkeypatch.setattr(job_db_backup, "push_job_db_to_blob", lambda: calls.append(1))

    job_id = job_store.new_job_id()
    _seed_upload("broken.pdf", job_id)

    with pytest.raises(RuntimeError):
        run_pipeline("broken.pdf", job_id=job_id)

    assert calls == [1]
    assert job_store.get_job(job_id)["status"] == "FAILED"
