"""
agents/data_analyst.py
Data Analyst Agent
──────────────────
Responsibilities:
  1. Reads the DB schema (SQL Toolkit → get_schema)
  2. Translates the natural-language question into SQL
  3. Executes the query (SQL Toolkit → execute_sql)
  4. Writes a concise data summary

LangGraph nodes exposed:
  • node_generate_sql
  • node_execute_sql
  • node_data_summary
"""

import re, json
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from utils.db import get_schema, run_query
from utils.state import WorkflowState


def _llm():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)


# ── Node 1 ─────────────────────────────────────────────────────────────────────
def node_generate_sql(state: WorkflowState) -> WorkflowState:
    """Data Analyst Agent: translate question → SQL using schema context."""
    schema = get_schema()
    llm    = _llm()

    system = f"""You are a senior SQL Data Analyst at a bank.
You have access to the following SQLite database schema:

{schema}

Your task:
- Write a single, correct SELECT query that answers the user's question.
- Output ONLY the raw SQL — no markdown, no backticks, no explanation.
- Use meaningful column aliases (e.g. COUNT(*) AS total_loans).
- Limit results to 500 rows unless the question implies otherwise.
- Never use DROP, DELETE, INSERT, UPDATE, or CREATE.
"""
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=state["question"]),
    ]
    response = _llm().invoke(messages)
    sql = response.content.strip()
    sql = re.sub(r"^```(?:sql)?", "", sql, flags=re.IGNORECASE).strip()
    sql = re.sub(r"```$", "", sql).strip()

    return {**state, "sql": sql, "sql_error": None}


# ── Node 2 ─────────────────────────────────────────────────────────────────────
def node_execute_sql(state: WorkflowState) -> WorkflowState:
    """SQL Toolkit: execute the generated query against Finance DB."""
    if state.get("sql_error"):
        return state
    try:
        df = run_query(state["sql"])
        return {**state, "df": df, "sql_error": None}
    except Exception as exc:
        return {**state, "df": None, "sql_error": str(exc)}


# ── Node 3 ─────────────────────────────────────────────────────────────────────
def node_data_summary(state: WorkflowState) -> WorkflowState:
    """Data Analyst Agent: write a concise factual summary of the results."""
    if state.get("sql_error"):
        return {**state, "data_summary": f"Query failed: {state['sql_error']}"}

    df      = state["df"]
    preview = df.head(10).to_string(index=False) if df is not None else "No data."
    llm     = _llm()

    system = (
        "You are a concise data analyst. "
        "Given the query results, write 2-3 factual sentences highlighting "
        "key numbers and patterns. Be specific — include actual figures."
    )
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=(
            f"Question: {state['question']}\n\n"
            f"Result preview (first 10 rows):\n{preview}\n\n"
            f"Total rows returned: {len(df)}"
        )),
    ]
    response = llm.invoke(messages)
    return {**state, "data_summary": response.content.strip()}
