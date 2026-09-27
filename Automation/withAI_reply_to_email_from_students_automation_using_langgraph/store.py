"""
Tiny persistence layer so the agent doesn't reprocess an email (and
re-draft a reply, or worse, create a duplicate draft) across runs.

Kept deliberately separate from gmail_service.py (that's "the world the
agent acts on") and graph.py (that's "the agent's thinking"). This file is
just "what has the agent already done" -- a single, boring SQLite table.

Teaching note: this is intentionally the simplest possible persistence.
A real deployment might swap this for Postgres, or add a TTL/cleanup job,
but the interface (is_already_processed / mark_as_processed) wouldn't need
to change for callers.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import config

DB_PATH = Path(config.PROJECT_ROOT) / "processed_emails.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_emails (
    email_id     TEXT PRIMARY KEY,
    subject      TEXT,
    email_type   TEXT,
    status       TEXT,
    draft_id     TEXT,
    processed_at TEXT NOT NULL
);
"""


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the table if it doesn't exist yet. Safe to call every run."""
    with _connect() as conn:
        conn.execute(_SCHEMA)


def is_already_processed(email_id: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM processed_emails WHERE email_id = ?", (email_id,)
        ).fetchone()
    return row is not None


def mark_as_processed(
    email_id: str,
    subject: str = "",
    email_type: str = "",
    status: str = "",
    draft_id: str = "",
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO processed_emails
                (email_id, subject, email_type, status, draft_id, processed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(email_id) DO UPDATE SET
                subject=excluded.subject,
                email_type=excluded.email_type,
                status=excluded.status,
                draft_id=excluded.draft_id,
                processed_at=excluded.processed_at
            """,
            (
                email_id,
                subject,
                email_type,
                status,
                draft_id,
                datetime.now(timezone.utc).isoformat(),
            ),
        )