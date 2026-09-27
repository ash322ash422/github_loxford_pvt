"""
SQLite logging for the student email agent.

Two tables:
  - emails: one summary row per processed email (quick overview)
  - events: one row per pipeline step, timestamped (the actual chronology --
            "classified -> extracted -> policy_decision -> draft -> saved")

Usage in your pipeline (main.py / demo.py), after the graph finishes:

    from db_logger import init_db, log_event, log_email_result

    init_db()  # call once at startup

    final_state = student_email_agent.invoke(email)
    log_event(email["email_id"], "classify", final_state["classification"].email_type)
    ...
    log_email_result(final_state, gmail_draft_id=draft_id)

Or, more simply, just call log_email_result(final_state, draft_id) once at
the end -- it captures everything needed for a professor to understand what
happened, even without per-step events.

Run this file directly to just initialize the DB file:
    python db_logger.py
"""
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).parent / "logger.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS emails (
    email_id TEXT PRIMARY KEY,
    thread_id TEXT,
    sender TEXT,
    subject TEXT,
    email_type TEXT,
    is_relevant INTEGER,
    student_name TEXT,
    roll_number TEXT,
    course_code TEXT,
    reason TEXT,
    policy_decision TEXT,
    days_granted INTEGER,
    requires_documentation INTEGER,
    draft_subject TEXT,
    draft_body TEXT,
    gmail_draft_id TEXT,
    final_status TEXT,
    processed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id TEXT NOT NULL,
    step TEXT NOT NULL,
    detail TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (email_id) REFERENCES emails(email_id)
);
"""


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create the tables if they don't exist yet. Safe to call every run."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)


def log_event(email_id: str, step: str, detail: str = ""):
    """Record one step in the pipeline for a given email (chronological trail)."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO events (email_id, step, detail, timestamp) VALUES (?, ?, ?, ?)",
            (email_id, step, detail, datetime.now(timezone.utc).isoformat()),
        )


def log_email_result(state: dict, gmail_draft_id: str | None = None):
    """
    Call once per email after the LangGraph run finishes. Writes/updates the
    summary row in `emails` and adds a final 'completed' event. `state` is
    the dict returned by student_email_agent.invoke(...).
    """
    email_id = state["email_id"]
    classification = state.get("classification")
    info = state.get("student_info")
    decision = state.get("policy_decision")
    draft = state.get("draft_reply")

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO emails (
                email_id, thread_id, sender, subject, email_type, is_relevant,
                student_name, roll_number, course_code, reason,
                policy_decision, days_granted, requires_documentation,
                draft_subject, draft_body, gmail_draft_id, final_status, processed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(email_id) DO UPDATE SET
                email_type=excluded.email_type,
                is_relevant=excluded.is_relevant,
                student_name=excluded.student_name,
                roll_number=excluded.roll_number,
                course_code=excluded.course_code,
                reason=excluded.reason,
                policy_decision=excluded.policy_decision,
                days_granted=excluded.days_granted,
                requires_documentation=excluded.requires_documentation,
                draft_subject=excluded.draft_subject,
                draft_body=excluded.draft_body,
                gmail_draft_id=excluded.gmail_draft_id,
                final_status=excluded.final_status,
                processed_at=excluded.processed_at
            """,
            (
                email_id,
                state.get("thread_id"),
                state.get("sender"),
                state.get("subject"),
                classification.email_type if classification else None,
                int(state.get("is_relevant", False)),
                info.student_name if info else None,
                info.roll_number if info else None,
                info.course_code if info else None,
                info.reason if info else None,
                decision.decision if decision else None,
                decision.days_granted if decision else None,
                int(decision.requires_documentation) if decision else None,
                draft.subject if draft else None,
                draft.body if draft else None,
                gmail_draft_id,
                state.get("status"),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    log_event(email_id, "completed", state.get("status", ""))


def get_chronology(email_id: str | None = None) -> list[dict]:
    """
    Return the step-by-step event log, oldest first. Pass an email_id to
    scope it to one email, or leave blank for the full history.
    """
    with get_connection() as conn:
        if email_id:
            rows = conn.execute(
                "SELECT * FROM events WHERE email_id = ? ORDER BY timestamp",
                (email_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM events ORDER BY timestamp").fetchall()
        return [dict(r) for r in rows]


def get_all_emails() -> list[dict]:
    """Return the summary table, newest first -- good for a quick professor overview."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM emails ORDER BY processed_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def print_chronology(email_id: str | None = None):
    """Pretty-print the log to the console, e.g. for a quick professor-facing readout."""
    for row in get_chronology(email_id):
        print(f"[{row['timestamp']}] {row['email_id']:<10} {row['step']:<15} {row['detail']}")


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")