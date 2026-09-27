"""
Unit tests for scripts/cleanup_old_jobs.py. All directories and the job
store are isolated to tmp_path, so nothing here touches the real
backend/data_uploads, output, logs, or job_flow_status.db.
"""
import sqlite3
from datetime import datetime, timedelta

import pytest

from app import config
from app.services import job_store
from scripts import cleanup_old_jobs

BLOB_NAME = "tender.pdf"


@pytest.fixture(autouse=True)
def isolated_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_UPLOAD_DIR", tmp_path / "data_uploads")
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(config, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(config, "JOBS_DB", tmp_path / "job_flow_status.db")
    monkeypatch.setattr(config, "UPLOAD_RETENTION_DAYS", 7)
    monkeypatch.setattr(config, "OUTPUT_LOGS_RETENTION_DAYS", 30)


def _timestamp(days_ago: int) -> str:
    return (datetime.now(config.IST) - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")


def _make_job(job_id: str, completed_at: str = None, status: str = "COMPLETED") -> None:
    job_store.update_job(job_id, blob_name=BLOB_NAME, status=status)
    if completed_at:
        job_store.update_job(job_id, status=status, completed_at=completed_at)


def _backdate_created_at(job_id: str, days_ago: int) -> None:
    """created_at is only ever set once, at insert (see job_store.update_job) -
    the public API can't rewrite it, so simulate a genuinely old/stuck job
    by updating the column directly."""
    conn = sqlite3.connect(config.JOBS_DB)
    conn.execute("UPDATE jobs SET created_at = ? WHERE job_id = ?", (_timestamp(days_ago), job_id))
    conn.commit()
    conn.close()


def _make_job_dirs(job_id: str) -> None:
    (config.DATA_UPLOAD_DIR / job_id).mkdir(parents=True)
    (config.DATA_UPLOAD_DIR / job_id / BLOB_NAME).write_bytes(b"pdf bytes")
    (config.OUTPUT_DIR / job_id).mkdir(parents=True)
    (config.OUTPUT_DIR / job_id / "tender.xlsx").write_bytes(b"xlsx bytes")
    (config.LOG_DIR / job_id).mkdir(parents=True)
    (config.LOG_DIR / job_id / "ocr.json").write_text("{}")


def test_removes_upload_dir_past_retention_but_keeps_output_logs_within_retention():
    job_id = job_store.new_job_id()
    _make_job(job_id, completed_at=_timestamp(10))  # past 7-day upload window, within 30-day one
    _make_job_dirs(job_id)

    result = cleanup_old_jobs.cleanup()

    assert result == 0
    assert not (config.DATA_UPLOAD_DIR / job_id).exists()
    assert (config.OUTPUT_DIR / job_id).exists()
    assert (config.LOG_DIR / job_id).exists()


def test_removes_output_and_logs_past_retention():
    job_id = job_store.new_job_id()
    _make_job(job_id, completed_at=_timestamp(40))  # past both windows
    _make_job_dirs(job_id)

    cleanup_old_jobs.cleanup()

    assert not (config.DATA_UPLOAD_DIR / job_id).exists()
    assert not (config.OUTPUT_DIR / job_id).exists()
    assert not (config.LOG_DIR / job_id).exists()


def test_keeps_everything_within_retention():
    job_id = job_store.new_job_id()
    _make_job(job_id, completed_at=_timestamp(1))
    _make_job_dirs(job_id)

    cleanup_old_jobs.cleanup()

    assert (config.DATA_UPLOAD_DIR / job_id).exists()
    assert (config.OUTPUT_DIR / job_id).exists()
    assert (config.LOG_DIR / job_id).exists()


def test_falls_back_to_created_at_for_stuck_job_with_no_completed_at():
    job_id = job_store.new_job_id()
    _make_job(job_id, completed_at=None, status="STARTED")
    _backdate_created_at(job_id, days_ago=40)
    _make_job_dirs(job_id)

    cleanup_old_jobs.cleanup()

    assert not (config.DATA_UPLOAD_DIR / job_id).exists()
    assert not (config.OUTPUT_DIR / job_id).exists()
    assert not (config.LOG_DIR / job_id).exists()


def test_dry_run_deletes_nothing():
    job_id = job_store.new_job_id()
    _make_job(job_id, completed_at=_timestamp(40))
    _make_job_dirs(job_id)

    result = cleanup_old_jobs.cleanup(dry_run=True)

    assert result == 0
    assert (config.DATA_UPLOAD_DIR / job_id).exists()
    assert (config.OUTPUT_DIR / job_id).exists()
    assert (config.LOG_DIR / job_id).exists()


def test_job_store_row_survives_file_cleanup():
    job_id = job_store.new_job_id()
    _make_job(job_id, completed_at=_timestamp(40))
    _make_job_dirs(job_id)

    cleanup_old_jobs.cleanup()

    assert job_store.get_job(job_id) is not None
    assert job_store.get_job(job_id)["status"] == "COMPLETED"


def test_handles_jobs_with_no_directories_on_disk_gracefully():
    job_id = job_store.new_job_id()
    _make_job(job_id, completed_at=_timestamp(40))
    # deliberately no _make_job_dirs(job_id) - nothing on disk for this job

    result = cleanup_old_jobs.cleanup()

    assert result == 0


# --- cleanup_if_due() - the gated version the API triggers opportunistically ---

def _write_marker(days_ago: int) -> None:
    marker = config.LOG_DIR / ".cleanup_last_run"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(_timestamp(days_ago))


def test_cleanup_if_due_runs_on_first_call_and_creates_marker():
    job_id = job_store.new_job_id()
    _make_job(job_id, completed_at=_timestamp(40))
    _make_job_dirs(job_id)

    ran = cleanup_old_jobs.cleanup_if_due()

    assert ran is True
    assert (config.LOG_DIR / ".cleanup_last_run").exists()
    assert not (config.DATA_UPLOAD_DIR / job_id).exists()  # cleanup actually happened


def test_cleanup_if_due_skips_within_interval():
    _write_marker(days_ago=0)  # "just ran"

    job_id = job_store.new_job_id()
    _make_job(job_id, completed_at=_timestamp(40))
    _make_job_dirs(job_id)

    ran = cleanup_old_jobs.cleanup_if_due()

    assert ran is False
    assert (config.DATA_UPLOAD_DIR / job_id).exists()  # nothing touched


def test_cleanup_if_due_runs_again_after_interval_elapses():
    _write_marker(days_ago=2)  # default interval is 1 day

    job_id = job_store.new_job_id()
    _make_job(job_id, completed_at=_timestamp(40))
    _make_job_dirs(job_id)

    ran = cleanup_old_jobs.cleanup_if_due()

    assert ran is True
    assert not (config.DATA_UPLOAD_DIR / job_id).exists()


def test_cleanup_if_due_respects_custom_min_interval():
    job_id = job_store.new_job_id()
    _make_job(job_id, completed_at=_timestamp(40))
    _make_job_dirs(job_id)

    assert cleanup_old_jobs.cleanup_if_due(min_interval_days=5) is True  # first call always runs
    assert cleanup_old_jobs.cleanup_if_due(min_interval_days=5) is False  # too soon for a 5-day gate
