"""
Unit tests for the SQLite-backed job_store. Each test gets its own
temp-file database via the isolated_db fixture, so nothing here touches
the real backend/cache/job_flow_status.db.
"""
import sqlite3
from datetime import datetime

import pytest

from app import config
from app.services import job_store


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "JOBS_DB", tmp_path / "jobs.db")


def test_update_job_creates_row_on_first_call():
    job_id = job_store.new_job_id()
    job = job_store.update_job(job_id, blob_name="tender.pdf", status="STARTED")

    assert job["job_id"] == job_id
    assert job["blob_name"] == "tender.pdf"
    assert job["status"] == "STARTED"
    assert job["token_count"] == 0
    assert job["ocr_page_count"] == 0


def test_update_job_merges_into_existing_row():
    job_id = job_store.new_job_id()
    job_store.update_job(job_id, blob_name="tender.pdf", status="STARTED")
    job = job_store.update_job(
        job_id, status="COMPLETED", token_count=123, ocr_page_count=7, download_url="out.xlsx"
    )

    assert job["status"] == "COMPLETED"
    assert job["token_count"] == 123
    assert job["ocr_page_count"] == 7
    assert job["download_url"] == "out.xlsx"
    assert job["blob_name"] == "tender.pdf"  # untouched fields survive the merge


def test_two_jobs_with_same_blob_name_stay_independent():
    """The whole point of keying by job_id instead of blob_name."""
    job_id_1 = job_store.new_job_id()
    job_id_2 = job_store.new_job_id()
    job_store.update_job(job_id_1, blob_name="tender.pdf", status="COMPLETED")
    job_store.update_job(job_id_2, blob_name="tender.pdf", status="FAILED")

    assert job_store.get_job(job_id_1)["status"] == "COMPLETED"
    assert job_store.get_job(job_id_2)["status"] == "FAILED"


def test_get_job_returns_none_for_unknown_id():
    assert job_store.get_job("does-not-exist") is None


def test_all_jobs_orders_most_recent_first():
    job_id_1 = job_store.new_job_id()
    job_store.update_job(job_id_1, blob_name="first.pdf", status="COMPLETED")
    job_id_2 = job_store.new_job_id()
    job_store.update_job(job_id_2, blob_name="second.pdf", status="COMPLETED")

    jobs = job_store.all_jobs()
    assert [j["job_id"] for j in jobs][:2] == [job_id_2, job_id_1]


def test_total_token_usage_sums_across_jobs():
    job_store.update_job(job_store.new_job_id(), blob_name="a.pdf", status="COMPLETED", token_count=10)
    job_store.update_job(job_store.new_job_id(), blob_name="b.pdf", status="COMPLETED", token_count=15)

    assert job_store.total_token_usage() == 25


def test_total_ocr_pages_processed_sums_across_jobs():
    job_store.update_job(job_store.new_job_id(), blob_name="a.pdf", status="COMPLETED", ocr_page_count=4)
    job_store.update_job(job_store.new_job_id(), blob_name="b.pdf", status="COMPLETED", ocr_page_count=9)

    assert job_store.total_ocr_pages_processed() == 13


def test_ocr_page_count_stays_zero_on_cache_hit_run():
    """A job that never actually called Document Intelligence (cache hit)
    should not be counted as having processed any pages."""
    job_id = job_store.new_job_id()
    job = job_store.update_job(job_id, blob_name="tender.pdf", status="COMPLETED", token_count=0)

    assert job["ocr_page_count"] == 0


def test_init_db_migrates_existing_database_missing_ocr_page_count():
    """Simulates a real backend/cache/job_flow_status.db from before
    ocr_page_count existed: a jobs table without that column, with a row
    already in it. init_db() must add the column (defaulting to 0)
    without losing the existing row."""
    conn = sqlite3.connect(config.JOBS_DB)
    conn.execute(
        """
        CREATE TABLE jobs (
            job_id TEXT PRIMARY KEY,
            blob_name TEXT NOT NULL,
            status TEXT NOT NULL,
            error TEXT,
            failed_stage TEXT,
            download_url TEXT,
            token_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            completed_at TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO jobs (job_id, blob_name, status, token_count, created_at, updated_at) "
        "VALUES ('old-job', 'legacy.pdf', 'COMPLETED', 50, '2026-01-01 00:00:00', '2026-01-01 00:00:00')"
    )
    conn.commit()
    conn.close()

    job_store.init_db()

    job = job_store.get_job("old-job")
    assert job["blob_name"] == "legacy.pdf"
    assert job["token_count"] == 50
    assert job["ocr_page_count"] == 0


def _insert_raw_job(job_id: str, blob_name: str, status: str, ocr_page_count: int, created_at: str) -> None:
    """Bypasses update_job's created_at=now() so a row can be planted in a
    month other than the current one - update_job has no way to override
    created_at on insert."""
    job_store.init_db()
    conn = sqlite3.connect(config.JOBS_DB)
    conn.execute(
        "INSERT INTO jobs (job_id, blob_name, status, ocr_page_count, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (job_id, blob_name, status, ocr_page_count, created_at, created_at),
    )
    conn.commit()
    conn.close()


def test_total_ocr_pages_processed_this_month_excludes_other_months():
    now = datetime.now(config.IST)
    _insert_raw_job("this-month", "a.pdf", "COMPLETED", 7, now.strftime("%Y-%m-%d %H:%M:%S"))
    _insert_raw_job("last-year", "b.pdf", "COMPLETED", 100, "2020-01-01 00:00:00")

    assert job_store.total_ocr_pages_processed_this_month(now) == 7


def test_jobs_this_month_excludes_other_months_and_orders_most_recent_first():
    now = datetime.now(config.IST)
    _insert_raw_job("this-month", "a.pdf", "COMPLETED", 7, now.strftime("%Y-%m-%d %H:%M:%S"))
    _insert_raw_job("last-year", "b.pdf", "COMPLETED", 100, "2020-01-01 00:00:00")

    jobs = job_store.jobs_this_month(now)
    assert [j["job_id"] for j in jobs] == ["this-month"]
