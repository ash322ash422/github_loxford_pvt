"""
agents/reporting_agent.py
Reporting Agent
───────────────
Responsibilities:
  1. Decides the best chart type for the data (Visualization Toolkit)
  2. Writes a full 3-5 paragraph narrative report
  3. Builds the PDF (PDF Generator)

LangGraph nodes exposed:
  • node_choose_chart
  • node_write_narrative
  • node_build_pdf
"""

import json
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from utils.state import WorkflowState
from reports.pdf_report import generate_pdf
from graphs.charts import build_chart


def _llm():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.3)


# ── Node 4 ─────────────────────────────────────────────────────────────────────
def node_choose_chart(state: WorkflowState) -> WorkflowState:
    """Visualization Toolkit: decide chart type and title from the data shape."""
    if state.get("sql_error") or state["df"] is None:
        return {**state, "chart_type": None, "chart_title": "No Data"}

    df = state["df"]
    col_info = {c: str(df[c].dtype) for c in df.columns}
    llm      = _llm()

    system = """You are a data visualisation expert.
Given a DataFrame description, decide the best chart type.
Reply with ONLY a JSON object like:
{"chart_type": "bar", "title": "Total Loans by City"}

chart_type must be one of: bar, line, scatter, pie, histogram

Rules:
- bar       → category vs numeric (counts, sums, averages by group)
- line      → time series or ordered sequence
- scatter   → two numeric variables correlated
- pie       → share/proportion of a small number of categories (≤8)
- histogram → distribution of a single numeric variable
"""
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=(
            f"Question: {state['question']}\n"
            f"Columns and dtypes: {col_info}\n"
            f"Row count: {len(df)}\n"
            f"Sample (3 rows):\n{df.head(3).to_string(index=False)}"
        )),
    ]
    raw = _llm().invoke(messages).content.strip()

    # Parse safely
    try:
        raw_clean = raw.strip().strip("```json").strip("```").strip()
        parsed    = json.loads(raw_clean)
        chart_type  = parsed.get("chart_type", "bar")
        chart_title = parsed.get("title", state["question"][:60])
    except Exception:
        chart_type  = "bar"
        chart_title = state["question"][:60]

    return {**state, "chart_type": chart_type, "chart_title": chart_title}


# ── Node 5 ─────────────────────────────────────────────────────────────────────
def node_write_narrative(state: WorkflowState) -> WorkflowState:
    """Reporting Agent: write a full analytical narrative report."""
    if state.get("sql_error"):
        return {**state, "report_narrative": f"Analysis could not be completed.\n\nError: {state['sql_error']}"}

    df      = state["df"]
    preview = df.head(15).to_string(index=False) if df is not None else "No data."
    llm     = _llm()

    system = """You are a senior financial analyst writing an internal bank report.
Write a structured 3-5 paragraph narrative that includes:
1. Executive Summary — what was asked, what was found
2. Key Findings — specific numbers, top/bottom performers, outliers
3. Trends & Patterns — any notable patterns in the data
4. Business Recommendations — 2-3 actionable suggestions based on the data
Use professional but clear language. Do NOT use markdown headers or bullet points.
Write in flowing paragraphs.
"""
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=(
            f"Question: {state['question']}\n\n"
            f"SQL used:\n{state.get('sql','N/A')}\n\n"
            f"Data ({len(df)} rows total, first 15 shown):\n{preview}\n\n"
            f"Data summary: {state.get('data_summary','')}"
        )),
    ]
    narrative = llm.invoke(messages).content.strip()
    return {**state, "report_narrative": narrative}


# ── Node 6 ─────────────────────────────────────────────────────────────────────
def node_build_pdf(state: WorkflowState) -> WorkflowState:
    """PDF Generator: assemble chart + narrative + data table into a PDF."""
    df  = state.get("df")
    fig = None

    if df is not None and not df.empty:
        fig = build_chart(
            df           = df,
            chart_type   = state.get("chart_type", "bar"),
            title        = state.get("chart_title", state["question"][:60]),
        )

    pdf_bytes = generate_pdf(
        question  = state["question"],
        sql       = state.get("sql", ""),
        df        = df if df is not None else pd.DataFrame(),
        summary   = state.get("data_summary", ""),
        narrative = state.get("report_narrative", ""),
        fig       = fig,
    )
    return {**state, "pdf_bytes": pdf_bytes}
