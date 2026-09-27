"""
agents/fraud_scorer_agent.py
Fraud Scorer Agent
──────────────────
Runs the Fraud Toolkit: amount anomaly, velocity, geo mismatch, channel risk.
Aggregates signals into a composite fraud score.

LangGraph node: node_fraud_scorer_agent
"""

import json, time
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from utils.state import WorkflowState
from toolkits.fraud_toolkit import (
    check_amount_anomaly,
    check_velocity,
    check_geo_mismatch,
    check_channel_risk,
)
from utils.db import fetch_one


def _llm():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)


def node_fraud_scorer_agent(state: WorkflowState) -> WorkflowState:
    """
    Fraud Scorer Agent: runs four rule-based fraud signals
    then asks the LLM to synthesise them into a composite score.
    """
    t0  = time.time()
    txn = state["transaction"]

    # ── Fetch customer country for geo check ──────────────────────────
    customer = fetch_one(
        "SELECT country FROM customers WHERE customer_id = ?",
        (txn["customer_id"],),
    )
    customer_country = customer["country"] if customer else "UNKNOWN"

    # ── Run all four fraud toolkit checks ────────────────────────────
    amount_signal  = json.loads(check_amount_anomaly.invoke({
        "customer_id": txn["customer_id"],
        "amount":      txn["amount"],
    }))
    velocity_signal = json.loads(check_velocity.invoke({
        "customer_id":    txn["customer_id"],
        "window_minutes": 60,
    }))
    geo_signal = json.loads(check_geo_mismatch.invoke({
        "customer_country": customer_country,
        "merchant_country": txn["merchant_country"],
        "amount":           txn["amount"],
    }))
    channel_signal = json.loads(check_channel_risk.invoke({
        "channel": txn["channel"],
    }))

    signals = {
        "amount_anomaly": amount_signal,
        "velocity":       velocity_signal,
        "geo_mismatch":   geo_signal,
        "channel_risk":   channel_signal,
    }

    # ── LLM synthesises composite score ─────────────────────────────
    llm    = _llm()
    system = """You are a fraud scoring engine. Given four risk signals,
return ONLY a JSON object:
{
  "risk_level": "low" | "medium" | "high" | "critical",
  "risk_score": 0.0 to 1.0,
  "flags": ["top 1-3 concerns, empty if none"],
  "summary": "one sentence"
}
Weight: amount anomaly=35%, velocity=30%, geo=25%, channel=10%.
No markdown. Raw JSON only."""

    prompt = f"Transaction: {json.dumps(txn)}\n\nSignals:\n{json.dumps(signals, indent=2)}"

    response = _llm().invoke([SystemMessage(content=system), HumanMessage(content=prompt)])

    try:
        result = json.loads(response.content.strip().strip("```json").strip("```"))
    except Exception:
        result = {
            "risk_level": "medium",
            "risk_score": 0.5,
            "flags":      ["parse error"],
            "summary":    "Fraud scoring inconclusive",
        }

    result["signals"]    = signals
    elapsed_ms           = round((time.time() - t0) * 1000)
    result["elapsed_ms"] = elapsed_ms

    timing = state.get("timing") or {}
    timing["fraud_scorer_ms"] = elapsed_ms

    return {"fraud_result": result, "timing": timing}
    # return {**state, "fraud_result": result, "timing": timing}
