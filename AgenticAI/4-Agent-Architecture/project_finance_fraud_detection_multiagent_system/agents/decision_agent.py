"""
agents/decision_agent.py
Decision Agent
──────────────
Waits for all three parallel agents to finish, then merges their
risk signals into a final APPROVE / FLAG / BLOCK decision.

LangGraph node: node_decision_agent
"""

import json, time
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from utils.state import WorkflowState


def _llm():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)


def node_decision_agent(state: WorkflowState) -> WorkflowState:
    """
    Decision Agent: aggregates history, fraud score, and blacklist
    results into a final decision with explanation.
    """
    t0 = time.time()

    history   = state.get("history_result", {})
    fraud     = state.get("fraud_result", {})
    blacklist = state.get("blacklist_result", {})
    txn       = state["transaction"]

    # ── Hard rule: any blacklist hit → immediate BLOCK ────────────────
    if blacklist and blacklist.get("any_hit"):
        decision   = "BLOCK"
        risk_score = 1.0
        reasons    = blacklist.get("hits", [])
        explanation = (
            f"Transaction BLOCKED. Blacklist hits detected: {'; '.join(reasons)}. "
            f"No further analysis required."
        )
        elapsed_ms = round((time.time() - t0) * 1000)
        timing = state.get("timing") or {}
        timing["decision_agent_ms"] = elapsed_ms
        timing["total_ms"] = sum(timing.values())
        return {**state,
                "decision": decision, "risk_score": risk_score,
                "reasons": reasons, "explanation": explanation,
                "timing": timing}

    # ── Weighted composite score ──────────────────────────────────────
    h_score = history.get("risk_score", 0.5) if history else 0.5
    f_score = fraud.get("risk_score",   0.5) if fraud   else 0.5
    b_score = blacklist.get("risk_score", 0.0) if blacklist else 0.0

    composite = round(
        h_score * 0.30 +   # history weight
        f_score * 0.50 +   # fraud signals weight
        b_score * 0.20,    # blacklist weight
        3,
    )

    # ── LLM makes final decision ─────────────────────────────────────
    llm    = _llm()
    system = """You are the final fraud decision engine at a bank.
Given three agent risk assessments and a composite score, output ONLY JSON:
{
  "decision": "APPROVE" | "FLAG" | "BLOCK",
  "risk_score": 0.0 to 1.0,
  "reasons": ["up to 4 key reasons"],
  "explanation": "2-3 sentence explanation for the compliance team"
}

Decision rules:
- APPROVE  → composite < 0.35 and no critical signals
- FLAG     → composite 0.35-0.65 or any high signal
- BLOCK    → composite > 0.65 or any critical signal

No markdown. Raw JSON only."""

    context = {
        "transaction":       txn,
        "composite_score":   composite,
        "history_agent":     history,
        "fraud_scorer_agent": fraud,
        "blacklist_agent":   blacklist,
    }
    response = _llm().invoke([
        SystemMessage(content=system),
        HumanMessage(content=json.dumps(context, indent=2)),
    ])

    try:
        result = json.loads(response.content.strip().strip("```json").strip("```"))
    except Exception:
        result = {
            "decision":    "FLAG",
            "risk_score":  composite,
            "reasons":     ["parse error in decision agent"],
            "explanation": "Decision engine encountered an error; flagged for manual review.",
        }

    elapsed_ms = round((time.time() - t0) * 1000)
    timing = state.get("timing") or {}
    timing["decision_agent_ms"] = elapsed_ms
    timing["total_ms"] = sum(timing.values())

    return {
        **state,
        "decision":    result.get("decision", "FLAG"),
        "risk_score":  result.get("risk_score", composite),
        "reasons":     result.get("reasons", []),
        "explanation": result.get("explanation", ""),
        "timing":      timing,
    }
