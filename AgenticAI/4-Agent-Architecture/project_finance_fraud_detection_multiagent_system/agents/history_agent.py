"""
agents/history_agent.py
History Agent
─────────────
Runs the SQL Toolkit to pull customer profile, recent transactions,
and historical fraud rate. Returns a structured risk assessment.

LangGraph node: node_history_agent
"""

import json, time
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from utils.state import WorkflowState
from toolkits.sql_toolkit import (
    get_customer_profile,
    get_recent_txns,
    get_fraud_rate,
)


def _llm():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)


def node_history_agent(state: WorkflowState) -> WorkflowState:
    """
    History Agent: analyses customer's past behaviour.
    Uses SQL Toolkit to fetch profile, recent transactions, and fraud rate.
    """
    t0  = time.time()
    txn = state["transaction"]

    # ── Step 1: Pull raw data via toolkit ────────────────────────────
    profile_json  = get_customer_profile.invoke({"customer_id": txn["customer_id"]})
    recent_json   = get_recent_txns.invoke({"customer_id": txn["customer_id"], "limit": 10})
    fraud_rate_json = get_fraud_rate.invoke({"customer_id": txn["customer_id"]})

    profile    = json.loads(profile_json)
    recent     = json.loads(recent_json)
    fraud_rate = json.loads(fraud_rate_json)

    # ── Step 2: LLM analyses the data and returns structured risk ────
    llm    = _llm()
    system = """You are a bank fraud analyst reviewing customer history.
Analyse the data and return ONLY a JSON object with these keys:
{
  "risk_level": "low" | "medium" | "high" | "critical",
  "risk_score": 0.0 to 1.0,
  "flags": ["list of specific concerns, empty if none"],
  "summary": "one sentence summary"
}
No markdown, no explanation. Raw JSON only."""

    prompt = f"""Current transaction: amount={txn['amount']} {txn['currency']}, merchant={txn['merchant']}

Customer profile: {json.dumps(profile, indent=2)}
Recent transactions (last 10): {json.dumps(recent, indent=2)}
Historical fraud rate: {json.dumps(fraud_rate, indent=2)}"""

    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=prompt)])

    try:
        result = json.loads(response.content.strip().strip("```json").strip("```"))
    except Exception:
        result = {
            "risk_level": "medium",
            "risk_score": 0.5,
            "flags":      ["could not parse LLM response"],
            "summary":    "History analysis inconclusive",
        }

    elapsed_ms = round((time.time() - t0) * 1000)
    result["elapsed_ms"] = elapsed_ms

    timing = state.get("timing") or {}
    timing["history_agent_ms"] = elapsed_ms

    return {"history_result": result, "timing": timing}
    # return {**state, "history_result": result, "timing": timing}
