"""
utils/db.py — SQLite helpers: schema extraction and safe query execution.
"""

import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "database" / "lending.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def get_schema() -> str:
    """Return a human-readable schema string for the LLM prompt."""
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [r[0] for r in cur.fetchall()]

    lines = []
    for table in tables:
        cur.execute(f"PRAGMA table_info({table});")
        cols = cur.fetchall()
        col_defs = ", ".join(f"{c[1]} ({c[2]})" for c in cols)
        lines.append(f"Table: {table}\n  Columns: {col_defs}")

    conn.close()
    return "\n\n".join(lines)


def run_query(sql: str) -> pd.DataFrame:
    """Execute a SELECT query and return results as a DataFrame."""
    conn = get_connection()
    try:
        df = pd.read_sql_query(sql, conn)
    finally:
        conn.close()
    return df
