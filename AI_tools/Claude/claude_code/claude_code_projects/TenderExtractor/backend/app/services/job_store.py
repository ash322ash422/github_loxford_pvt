# job_store.py
"""
Tracks the status of every pipeline run in a SQLite database, one row per
run, keyed by job_id (a UUID generated per run - see new_job_id()).

Keyed by job_id rather than blob_name so that re-processing the same
filename (or two different users uploading a file with the same name)
never overwrites another run's status - the old version keyed a single
JSON file by blob_name, which meant exactly that collision.
"""
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Optional

from app import config


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.JOBS_DB, timeout=30)
    conn.row_factory = sqlite3.Row
    # NOT WAL: config.JOBS_DB lives under LOCAL_STATE_DIR specifically so it
    # never ends up on a network-mounted volume (e.g. Azure Files) - WAL
    # mode's shared-memory-mapped locking (-shm/-wal companion files) fails
    # there with "database is locked", confirmed in production. The classic
    # rollback-journal mode works everywhere (local disk or network), so it
    # stays the default even now that the DB is guaranteed local - no upside
    # to WAL for this light, mostly-single-writer load worth the extra mode.
    conn.execute("PRAGMA journal_mode=DELETE")
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                blob_name TEXT NOT NULL,
                status TEXT NOT NULL,
                error TEXT,
                failed_stage TEXT,
                download_url TEXT,
                token_count INTEGER NOT NULL DEFAULT 0,
                ocr_page_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT
            )
            """
        )
        # Migration for databases created before ocr_page_count existed -
        # CREATE TABLE IF NOT EXISTS above is a no-op on an existing table.
        existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)")}
        if "ocr_page_count" not in existing_columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN ocr_page_count INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    finally:
        conn.close()


def new_job_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(config.IST).strftime("%Y-%m-%d %H:%M:%S")


def update_job(job_id: str, **fields: Any) -> dict:
    """
    Upsert: creates the row the first time a job_id is seen (using
    `fields` for the initial values, defaulting status to PENDING),
    otherwise merges `fields` into the existing row. Mirrors the old
    JSON-backed job_store's "create or merge" behaviour.
    """
    init_db()
    now = _now()
    conn = _connect()
    try:
        existing = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()

        if existing is None:
            row = {
                "job_id": job_id,
                "blob_name": fields.get("blob_name", ""),
                "status": fields.get("status", "PENDING"),
                "error": fields.get("error"),
                "failed_stage": fields.get("failed_stage"),
                "download_url": fields.get("download_url"),
                "token_count": fields.get("token_count", 0),
                "ocr_page_count": fields.get("ocr_page_count", 0),
                "created_at": now,
                "updated_at": now,
                "completed_at": fields.get("completed_at"),
            }
            conn.execute(
                """
                INSERT INTO jobs
                    (job_id, blob_name, status, error, failed_stage, download_url,
                     token_count, ocr_page_count, created_at, updated_at, completed_at)
                VALUES
                    (:job_id, :blob_name, :status, :error, :failed_stage, :download_url,
                     :token_count, :ocr_page_count, :created_at, :updated_at, :completed_at)
                """,
                row,
            )
        else:
            merged = dict(existing)
            merged.update(fields)
            merged["updated_at"] = now
            conn.execute(
                """
                UPDATE jobs SET
                    blob_name = :blob_name, status = :status, error = :error,
                    failed_stage = :failed_stage, download_url = :download_url,
                    token_count = :token_count, ocr_page_count = :ocr_page_count,
                    updated_at = :updated_at, completed_at = :completed_at
                WHERE job_id = :job_id
                """,
                merged,
            )

        conn.commit()
        return dict(conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone())
    finally:
        conn.close()


def get_job(job_id: str) -> Optional[dict]:
    init_db()
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def all_jobs() -> list[dict]:
    """
    Every job, most recently created first. created_at only has
    second-level resolution, so rowid (insertion order) breaks ties
    between jobs created within the same second.
    """
    init_db()
    conn = _connect()
    try:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC, rowid DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def total_token_usage() -> int:
    init_db()
    conn = _connect()
    try:
        row = conn.execute("SELECT COALESCE(SUM(token_count), 0) AS total FROM jobs").fetchone()
        return row["total"]
    finally:
        conn.close()


def total_ocr_pages_processed() -> int:
    """Sum of ocr_page_count across every job - pages actually billed by
    Document Intelligence (cache hits contribute 0, same as token_count)."""
    init_db()
    conn = _connect()
    try:
        row = conn.execute("SELECT COALESCE(SUM(ocr_page_count), 0) AS total FROM jobs").fetchone()
        return row["total"]
    finally:
        conn.close()


def total_ocr_pages_processed_this_month(reference_date: Optional[datetime] = None) -> int:
    """
    Sum of ocr_page_count for jobs created in the current IST month.
    Bucketed on created_at (not completed_at) - a job has already had its
    pages billed the moment its OCR stage ran, well before it completes (or
    even if it later fails), so this must count it before then too.
    """
    init_db()
    month_prefix = (reference_date or datetime.now(config.IST)).strftime("%Y-%m")
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(ocr_page_count), 0) AS total FROM jobs WHERE created_at LIKE ?",
            (f"{month_prefix}%",),
        ).fetchone()
        return row["total"]
    finally:
        conn.close()


def jobs_this_month(reference_date: Optional[datetime] = None) -> list[dict]:
    """Every job created in the current IST month, most recent first."""
    init_db()
    month_prefix = (reference_date or datetime.now(config.IST)).strftime("%Y-%m")
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE created_at LIKE ? ORDER BY created_at DESC, rowid DESC",
            (f"{month_prefix}%",),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
