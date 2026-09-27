"""
state.py
---------
INDUSTRY PATTERN: one shared, typed state object flows through the
whole graph.

In the hand-rolled version of this project, each agent's `run()`
returned a plain dict that the orchestrator manually threaded into the
next agent's `run()` call. LangGraph formalizes that same idea: you
declare one `TypedDict` describing everything the pipeline carries, and
every node receives the current state and returns a partial update to
it. LangGraph merges updates into the running state automatically and
persists the whole thing via the checkpointer after every node --
that's what gives us resumability for free (see graph.py).
"""

from typing import TypedDict


class PipelineState(TypedDict, total=False):
    # ---- input ----
    csv_path: str

    # ---- produced by data_node ----
    campaign_data: list[dict]
    benchmarks: dict
    data_agent_summary: str

    # ---- produced by analytics_node ----
    kpis: dict
    analytics_notes: str

    # ---- produced by escalation_node (an orchestrator-level decision,
    # not owned by any single agent) ----
    escalate: bool

    # ---- produced by copilot_node ----
    decisions: dict          # deterministic rule-engine output, channel -> action
    applied: dict             # channel -> {status, action, rationale, approved}
    copilot_summary: str

    # ---- final assembled output ----
    final_report: str
