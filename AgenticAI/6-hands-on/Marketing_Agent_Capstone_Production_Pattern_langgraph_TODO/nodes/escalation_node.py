"""
nodes/escalation_node.py
---------------------------
A small orchestrator-level decision that doesn't belong to any single
agent -- the LangGraph equivalent of the `all_losing_money` check that
used to live directly in the hand-rolled Orchestrator class. Here it's
just an ordinary node sitting between analytics and copilot in the
graph. There's nothing agent-like about it (no LLM, no tools) -- which
is exactly the point: not every step in a pipeline needs to be an
agent, and LangGraph nodes are a natural home for plain conditional
logic that sits between agents.
"""

from state import PipelineState
from logging_config import get_logger

log = get_logger("Orchestrator")


def escalation_node(state: PipelineState) -> dict:
    kpis = state["kpis"]
    all_losing_money = all(kpi["roas"] < 1 for kpi in kpis.values())
    if all_losing_money:
        log.warning("ALERT: every channel is losing money -- escalating priority")
    return {"escalate": all_losing_money}
