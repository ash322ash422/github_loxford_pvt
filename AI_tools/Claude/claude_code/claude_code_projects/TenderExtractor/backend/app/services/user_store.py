# user_store.py
"""
Accounts for API login, one row per username, in their own SQLite database
(config.USERS_DB) - kept separate from job_flow_status.db so wiping/backing
up job history never touches accounts, and vice versa.

Mirrors job_store.py's shape: init_db() is safe to call on every request,
_connect() opens a short-lived connection per call rather than holding one
open, and everything returns plain dicts.
"""
import sqlite3
from datetime import datetime
from typing import Optional

from app import config


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.USERS_DB, timeout=30)
    conn.row_factory = sqlite3.Row
    # Same reasoning as job_store._connect(): USERS_DB lives under
    # LOCAL_STATE_DIR specifically so it stays on local disk, so there's no
    # network-filesystem locking issue WAL mode would otherwise dodge -
    # rollback-journal mode is the simpler default with no downside here.
    conn.execute("PRAGMA journal_mode=DELETE")
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _now() -> str:
    return datetime.now(config.IST).strftime("%Y-%m-%d %H:%M:%S")


def create_user(username: str, password_hash: str, role: str) -> dict:
    """Raises sqlite3.IntegrityError if `username` already exists - the API
    layer translates that into a 409."""
    init_db()
    now = _now()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO users (username, password_hash, role, created_at, updated_at)
            VALUES (:username, :password_hash, :role, :created_at, :updated_at)
            """,
            {
                "username": username,
                "password_hash": password_hash,
                "role": role,
                "created_at": now,
                "updated_at": now,
            },
        )
        conn.commit()
        return dict(conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone())
    finally:
        conn.close()


def get_user(username: str) -> Optional[dict]:
    init_db()
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_users() -> list[dict]:
    init_db()
    conn = _connect()
    try:
        rows = conn.execute("SELECT * FROM users ORDER BY username").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_user(username: str) -> bool:
    """Returns True if a row was actually deleted, False if `username` didn't exist."""
    init_db()
    conn = _connect()
    try:
        cursor = conn.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def update_password(username: str, password_hash: str) -> None:
    init_db()
    conn = _connect()
    try:
        conn.execute(
            "UPDATE users SET password_hash = ?, updated_at = ? WHERE username = ?",
            (password_hash, _now(), username),
        )
        conn.commit()
    finally:
        conn.close()


def count_users() -> int:
    init_db()
    conn = _connect()
    try:
        row = conn.execute("SELECT COUNT(*) AS total FROM users").fetchone()
        return row["total"]
    finally:
        conn.close()


def count_admins() -> int:
    init_db()
    conn = _connect()
    try:
        row = conn.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'admin'").fetchone()
        return row["total"]
    finally:
        conn.close()


def seed_initial_admin_if_empty(username: str, password_hash: str, role: str = "admin") -> None:
    """No-op unless the users table is completely empty - see auth.py's
    _ensure_seeded(), which calls this once per process using
    config.AUTH_USERNAME/AUTH_PASSWORD as the bootstrap admin."""
    if count_users() == 0:
        create_user(username, password_hash, role)
