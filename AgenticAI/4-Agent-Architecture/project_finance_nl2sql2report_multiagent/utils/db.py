"""utils/db.py — SQLite connection, schema, and safe query execution."""

import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path(__file__).parent.parent / "database" / "finance.db"


def get_schema() -> str:
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [r[0] for r in cur.fetchall()]
    lines  = []
    for t in tables:
        cur.execute(f"PRAGMA table_info({t});")
        cols = ", ".join(f"{c[1]} {c[2]}" for c in cur.fetchall())
        lines.append(f"Table: {t}\n  Columns: {cols}")
    conn.close()
    return "\n\n".join(lines)


def run_query(sql: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(sql, conn)
    finally:
        conn.close()
    return df
