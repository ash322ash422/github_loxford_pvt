"""
toolkits/sql_toolkit.py
Tools available to the Data Analyst Agent:
  • get_schema  — returns the DB schema as a string
  • execute_sql — runs a SELECT query and returns JSON rows
"""

import re
import json
from langchain_core.tools import tool
from utils.db import get_schema as _get_schema, run_query


@tool
def get_schema() -> str:
    """Return the full database schema (table names and columns)."""
    return _get_schema()


@tool
def execute_sql(sql: str) -> str:
    """
    Execute a read-only SQL SELECT statement against the Finance SQLite database.
    Returns up to 500 rows as a JSON string.
    Raises ValueError for non-SELECT queries.
    """
    clean = sql.strip()
    # Strip markdown fences if the LLM wrapped it
    clean = re.sub(r"^```(?:sql)?", "", clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r"```$", "", clean).strip()

    if not clean.upper().startswith("SELECT"):
        raise ValueError("Only SELECT statements are permitted.")

    df = run_query(clean)
    df = df.head(500)
    return df.to_json(orient="records", date_format="iso")
