"""utils/db.py — SQLite connection and helpers for fraud.db."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "database" / "fraud.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


def fetch_one(sql: str, params: tuple = ()) -> dict | None:
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()
    cur.execute(sql, params)
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]
