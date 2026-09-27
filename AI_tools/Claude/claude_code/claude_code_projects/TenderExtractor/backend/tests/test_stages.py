"""
Unit tests for the per-job file isolation added to stages.py:
- stage_ingest reads from the job-scoped upload path when present (the API
  flow), or falls back to a flat legacy path and copies it in (the CLI
  flow), or raises if neither exists.
- stages write an immutable per-job audit copy under logs/{job_id}/.

Azure calls (document_intelligence) are monkeypatched everywhere here, so
these never touch real services.
"""
import pytest

from app import config
from app.pipeline import exceptions, stages
from app.pipeline.context import PipelineContext
from app.services import document_intelligence

PDF_BYTES = b"%PDF-1.4 fake pdf bytes"


@pytest.fixture(autouse=True)
def isolated_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_UPLOAD_DIR", tmp_path / "data_uploads")
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(config, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(config, "AZURE_STORAGE_CONNECTION_STRING", None)


def _ctx(blob_name="tender.pdf", job_id="job-123") -> PipelineContext:
    return PipelineContext(blob_name=blob_name, job_id=job_id)


def test_stage_ingest_reads_from_job_scoped_path_when_already_present():
    """The API writes the upload directly to the job-scoped path before
    calling run_pipeline; stage_ingest should just read it, no copying."""
    ctx = _ctx()
    ctx.local_pdf_path.parent.mkdir(parents=True)
    ctx.local_pdf_path.write_bytes(PDF_BYTES)

    stages.stage_ingest(ctx)

    assert ctx.pdf_bytes == PDF_BYTES


def test_stage_ingest_falls_back_to_flat_legacy_path_and_copies_it_in():
    """CLI flow: file dropped flat into data_uploads/ before any job_id
    existed. stage_ingest must find it there and materialize a job-scoped
    copy, so this job gets its own isolated snapshot too."""
    ctx = _ctx()
    legacy_path = config.DATA_UPLOAD_DIR / ctx.blob_name
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_bytes(PDF_BYTES)

    assert not ctx.local_pdf_path.exists()  # sanity: nothing job-scoped yet

    stages.stage_ingest(ctx)

    assert ctx.pdf_bytes == PDF_BYTES
    assert ctx.local_pdf_path.exists()
    assert ctx.local_pdf_path.read_bytes() == PDF_BYTES


def test_stage_ingest_raises_when_file_is_nowhere():
    ctx = _ctx()
    with pytest.raises(FileNotFoundError):
        stages.stage_ingest(ctx)


def test_two_jobs_same_filename_get_independent_upload_copies():
    """The whole point: two jobs uploading a same-named file never share
    or overwrite each other's copy."""
    ctx_a = _ctx(blob_name="tender.pdf", job_id="job-a")
    ctx_b = _ctx(blob_name="tender.pdf", job_id="job-b")

    ctx_a.local_pdf_path.parent.mkdir(parents=True)
    ctx_a.local_pdf_path.write_bytes(b"content from job A")
    ctx_b.local_pdf_path.parent.mkdir(parents=True)
    ctx_b.local_pdf_path.write_bytes(b"content from job B")

    stages.stage_ingest(ctx_a)
    stages.stage_ingest(ctx_b)

    assert ctx_a.pdf_bytes == b"content from job A"
    assert ctx_b.pdf_bytes == b"content from job B"
    assert ctx_a.local_pdf_path != ctx_b.local_pdf_path


def test_stage_ocr_writes_audit_copy(monkeypatch):
    # stage_ocr no longer validates digital-ness itself - stage_ocr_preview
    # (which always runs first) already did, on the same immutable pdf_bytes.
    monkeypatch.setattr(document_intelligence, "analyze_document_from_bytes", lambda **kwargs: object())
    monkeypatch.setattr(
        document_intelligence, "extract_document_data",
        lambda result: {"pages": [{"page_number": 1, "text": "hello"}]},
    )

    ctx = _ctx()
    ctx.pdf_bytes = PDF_BYTES

    stages.stage_ocr(ctx)

    assert ctx.ocr_page_count == 1
    assert ctx.job_audit_path("ocr.json").exists()  # per-job audit copy written
    import json
    assert json.loads(ctx.job_audit_path("ocr.json").read_text()) == ctx.document_data


def test_stage_ocr_preview_writes_audit_copy(monkeypatch):
    monkeypatch.setattr(document_intelligence, "validate_pdf_is_digital", lambda pdf_bytes: True)
    monkeypatch.setattr(document_intelligence, "analyze_document_from_bytes", lambda **kwargs: object())
    monkeypatch.setattr(
        document_intelligence, "extract_document_data",
        lambda result: {"pages": [{"page_number": 1, "text": "hello"}]},
    )

    ctx = _ctx()
    ctx.pdf_bytes = PDF_BYTES

    stages.stage_ocr_preview(ctx)

    assert ctx.ocr_page_count == 1
    assert ctx.preview_document_data == {"pages": [{"page_number": 1, "text": "hello"}]}
    assert ctx.job_audit_path("ocr_preview.json").exists()


def test_ocr_page_count_sums_preview_and_full_pass(monkeypatch):
    """stage_ocr accumulates onto whatever stage_ocr_preview already
    counted, rather than overwriting it - the two OCR calls both count
    toward this job's page usage."""
    monkeypatch.setattr(document_intelligence, "validate_pdf_is_digital", lambda pdf_bytes: True)
    monkeypatch.setattr(document_intelligence, "analyze_document_from_bytes", lambda **kwargs: object())
    monkeypatch.setattr(
        document_intelligence, "extract_document_data",
        lambda result: {"pages": [{"page_number": i, "text": ""} for i in range(1, 4)]},
    )

    ctx = _ctx()
    ctx.pdf_bytes = PDF_BYTES

    stages.stage_ocr_preview(ctx)  # 3 preview pages
    stages.stage_ocr(ctx)          # "full" pass returns the same 3-page fake result again

    assert ctx.ocr_page_count == 6


def test_stage_check_index_and_tender_raises_when_no_keywords_found():
    ctx = _ctx()
    ctx.preview_document_data = {
        "pages": [{"page_number": 1, "text": "Just an ordinary letter, nothing official here."}]
    }

    with pytest.raises(exceptions.TenderCheckStopped):
        stages.stage_check_index_and_tender(ctx)

    assert ctx.is_tender is False


def test_stage_check_index_and_tender_extracts_index_when_tender_confirmed(monkeypatch):
    ctx = _ctx()
    ctx.preview_document_data = {
        "pages": [{"page_number": 1, "text": "NOTICE INVITING TENDER (NIT) No. 42/2026"}]
    }

    monkeypatch.setattr(
        stages.tender_index_extract_service, "extract_data",
        lambda pages, token_callback=None: {
            "terms_and_conditions_page": "44-48",
            "acceptable_make_page": None,
            "documents_to_be_scanned_page": "8",
        },
    )

    stages.stage_check_index_and_tender(ctx)

    assert ctx.is_tender is True
    assert ctx.extracted_index_data["terms_and_conditions_page"] == "44-48"
    assert ctx.job_audit_path("index.json").exists()
