"""
agents/workflow.py
LangGraph Workflow Orchestrator
────────────────────────────────
Wires the two agents into a single directed graph:

  [START]
     │
     ▼
  generate_sql        ← Data Analyst Agent
     │
     ▼
  execute_sql         ← SQL Toolkit
     │
     ▼
  data_summary        ← Data Analyst Agent
     │
     ├──────────────────┐
     ▼                  ▼
  choose_chart     write_narrative   ← Reporting Agent (parallel-ish, sequential here)
     │                  │
     └────────┬─────────┘
              ▼
          build_pdf          ← PDF Generator
              │
            [END]
            
"""

from langgraph.graph import StateGraph, END
from utils.state import WorkflowState

from agents.data_analyst import (
    node_generate_sql,
    node_execute_sql,
    node_data_summary,
)
from agents.reporting_agent import (
    node_choose_chart,
    node_write_narrative,
    node_build_pdf,
)


def build_workflow():
    graph = StateGraph(WorkflowState)

    # ── Data Analyst Agent nodes ───────────────────────────────────────────────
    graph.add_node("generate_sql",  node_generate_sql)   # NL → SQL
    graph.add_node("execute_sql",   node_execute_sql)    # SQL Toolkit
    graph.add_node("data_summary",  node_data_summary)   # Factual summary

    # ── Reporting Agent nodes ──────────────────────────────────────────────────
    graph.add_node("choose_chart",     node_choose_chart)     # Viz Toolkit
    graph.add_node("write_narrative",  node_write_narrative)  # Full report text
    graph.add_node("build_pdf",        node_build_pdf)        # PDF Generator

    # ── Edges ──────────────────────────────────────────────────────────────────
    graph.set_entry_point("generate_sql")
    graph.add_edge("generate_sql",    "execute_sql")
    graph.add_edge("execute_sql",     "data_summary")
    graph.add_edge("data_summary",    "choose_chart")
    graph.add_edge("choose_chart",    "write_narrative")
    graph.add_edge("write_narrative", "build_pdf")
    graph.add_edge("build_pdf",       END)

    return graph.compile()


def run_workflow(question: str) -> WorkflowState:
    app   = build_workflow()
    init  = WorkflowState(
        question         = question,
        sql              = None,
        df               = None,
        sql_error        = None,
        data_summary     = None,
        chart_type       = None,
        chart_title      = None,
        report_narrative = None,
        pdf_bytes        = None,
    )
    return app.invoke(init)
