"""
agents/workflow.py
LangGraph Workflow — Fraud Detection
─────────────────────────────────────
Uses Send API for true parallel execution of the three specialist agents.

Graph topology:

  [START]
     │
  orchestrator  ──── fans out via Send() ────┐
     │                                        │
     ├──► history_agent                       │  ← all three run
     ├──► fraud_scorer_agent                  │     in parallel
     └──► blacklist_agent ───────────────────┘
                                              │
                                      (join when all done)
                                              │
                                    decision_agent
                                              │
                                           [END]
"""

"""
agents/workflow.py
LangGraph Workflow — Fraud Detection
"""

from langgraph.graph import StateGraph, END, START
from langgraph.types import Send

from utils.state import WorkflowState
from agents.history_agent      import node_history_agent
from agents.fraud_scorer_agent import node_fraud_scorer_agent
from agents.blacklist_agent    import node_blacklist_agent
from agents.decision_agent     import node_decision_agent
import time


# Plain pass-through node — must return a dict
def orchestrator(state: WorkflowState) -> dict:
    return {}


# Routing function used in conditional edges — Send() is allowed here
def route_to_agents(state: WorkflowState) -> list[Send]:
    payload = dict(state)
    return [
        Send("history_agent",      payload),
        Send("fraud_scorer_agent", payload),
        Send("blacklist_agent",    payload),
    ]


def build_workflow():
    graph = StateGraph(WorkflowState)

    graph.add_node("orchestrator",       orchestrator)
    graph.add_node("history_agent",      node_history_agent)
    graph.add_node("fraud_scorer_agent", node_fraud_scorer_agent)
    graph.add_node("blacklist_agent",    node_blacklist_agent)
    graph.add_node("decision_agent",     node_decision_agent)

    graph.add_edge(START, "orchestrator")

    # Send() fan-out must come from a conditional_edges router in LangGraph 1.2.x
    graph.add_conditional_edges(
        "orchestrator",
        route_to_agents,
        ["history_agent", "fraud_scorer_agent", "blacklist_agent"],
    )

    graph.add_edge("history_agent",      "decision_agent")
    graph.add_edge("fraud_scorer_agent", "decision_agent")
    graph.add_edge("blacklist_agent",    "decision_agent")
    graph.add_edge("decision_agent",     END)

    return graph.compile()


def run_workflow(transaction: dict) -> WorkflowState:
    t_start = time.time()
    app     = build_workflow()
    init    = WorkflowState(
        transaction      = transaction,
        history_result   = None,
        fraud_result     = None,
        blacklist_result = None,
        decision         = None,
        risk_score       = None,
        reasons          = None,
        explanation      = None,
        timing           = {},
    )
    result = app.invoke(init)
    result["timing"]["wall_clock_ms"] = round((time.time() - t_start) * 1000)
    return result