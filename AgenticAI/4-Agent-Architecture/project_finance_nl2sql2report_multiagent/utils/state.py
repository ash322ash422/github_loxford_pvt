"""utils/state.py — Shared TypedDict that flows through the entire LangGraph."""

from typing import TypedDict, Optional
import pandas as pd


class WorkflowState(TypedDict):
    # ── input ──────────────────────────────────────────
    question:   str

    # ── Data Analyst Agent outputs ─────────────────────
    sql:        Optional[str]
    df:         Optional[pd.DataFrame]
    sql_error:  Optional[str]
    data_summary: Optional[str]

    # ── Reporting Agent outputs ────────────────────────
    chart_type: Optional[str]       # bar / line / scatter / pie / histogram
    chart_title: Optional[str]
    report_narrative: Optional[str]  # full written report text
    pdf_bytes:  Optional[bytes]
