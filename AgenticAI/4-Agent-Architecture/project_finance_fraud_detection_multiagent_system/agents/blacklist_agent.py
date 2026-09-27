"""
agents/blacklist_agent.py
Blacklist Agent
───────────────
Checks email, merchant, IP, and card against the blacklist database.
Any single hit is enough to escalate to BLOCK.

LangGraph node: node_blacklist_agent
"""

import json, time

from utils.state import WorkflowState
from toolkits.blacklist_toolkit import (
    check_email,
    check_merchant,
    check_ip,
    check_card,
)


def node_blacklist_agent(state: WorkflowState) -> WorkflowState:
    """
    Blacklist Agent: checks all available identifiers against
    the blacklist database. No LLM needed — purely deterministic.
    """
    t0  = time.time()
    txn = state["transaction"]

    checks = {}
    hits   = []

    # Email check
    if txn.get("customer_email"):
        r = json.loads(check_email.invoke({"email": txn["customer_email"]}))
        checks["email"] = r
        if r["hit"]:
            hits.append(f"Email blacklisted: {r['reason']}")

    # Merchant check
    r = json.loads(check_merchant.invoke({"merchant": txn["merchant"]}))
    checks["merchant"] = r
    if r["hit"]:
        hits.append(f"Merchant blacklisted: {r['reason']}")

    # IP check
    if txn.get("customer_ip"):
        r = json.loads(check_ip.invoke({"ip_address": txn["customer_ip"]}))
        checks["ip"] = r
        if r["hit"]:
            hits.append(f"IP blacklisted: {r['reason']}")

    # Card check
    if txn.get("card_number"):
        r = json.loads(check_card.invoke({"card_number": txn["card_number"]}))
        checks["card"] = r
        if r["hit"]:
            hits.append(f"Card blacklisted: {r['reason']}")

    elapsed_ms = round((time.time() - t0) * 1000)

    result = {
        "any_hit":     len(hits) > 0,
        "hits":        hits,
        "checks":      checks,
        "risk_level":  "critical" if hits else "low",
        "risk_score":  1.0 if hits else 0.0,
        "elapsed_ms":  elapsed_ms,
        "summary":     f"{len(hits)} blacklist hit(s) found" if hits else "No blacklist hits",
    }

    timing = state.get("timing") or {}
    timing["blacklist_agent_ms"] = elapsed_ms

    return {"blacklist_result": result, "timing": timing}
    # return {**state, "blacklist_result": result, "timing": timing}
