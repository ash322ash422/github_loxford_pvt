"""
toolkits/fraud_toolkit.py
Fraud scoring tools used by the Fraud Scorer Agent.
  • check_amount_anomaly   — is the amount unusual for this customer?
  • check_velocity         — too many transactions in a short window?
  • check_geo_mismatch     — does merchant country match customer country?
  • check_channel_risk     — is the channel high-risk?
"""

import json
from datetime import datetime, timedelta
from langchain_core.tools import tool
from utils.db import fetch_one, fetch_all


@tool
def check_amount_anomaly(customer_id: str, amount: float) -> str:
    """
    Compare the incoming transaction amount against the customer's
    historical average. Returns a risk signal if the amount is
    significantly above average (>3× avg is high risk, >10× is critical).
    """
    profile = fetch_one(
        "SELECT avg_txn_amount FROM customers WHERE customer_id = ?",
        (customer_id,),
    )
    if not profile:
        return json.dumps({"risk": "unknown", "reason": "customer not found"})

    avg    = profile["avg_txn_amount"]
    ratio  = round(amount / avg, 2) if avg > 0 else 999
    if ratio > 10:
        risk = "critical"
    elif ratio > 3:
        risk = "high"
    elif ratio > 1.5:
        risk = "medium"
    else:
        risk = "low"

    return json.dumps({
        "risk":   risk,
        "amount": amount,
        "avg":    round(avg, 2),
        "ratio":  ratio,
        "reason": f"Amount is {ratio}× the customer average",
    })


@tool
def check_velocity(customer_id: str, window_minutes: int = 60) -> str:
    """
    Count how many transactions the customer made in the last N minutes.
    >5 in 60 min is suspicious; >10 is high risk.
    """
    cutoff = (datetime.now() - timedelta(minutes=window_minutes)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    rows = fetch_all(
        """SELECT COUNT(*) AS cnt
           FROM transactions
           WHERE customer_id = ? AND txn_datetime >= ?""",
        (customer_id, cutoff),
    )
    cnt  = rows[0]["cnt"] if rows else 0
    risk = "critical" if cnt > 10 else "high" if cnt > 5 else "low"
    return json.dumps({
        "risk":            risk,
        "txn_count":       cnt,
        "window_minutes":  window_minutes,
        "reason":          f"{cnt} transactions in last {window_minutes} min",
    })


@tool
def check_geo_mismatch(
    customer_country: str,
    merchant_country: str,
    amount: float,
) -> str:
    """
    Flag when the merchant country differs from the customer's home country,
    especially on large amounts. Cross-border on >$1000 is elevated risk.
    """
    mismatch = customer_country != merchant_country
    if mismatch and amount > 1000:
        risk = "high"
    elif mismatch:
        risk = "medium"
    else:
        risk = "low"

    return json.dumps({
        "risk":             risk,
        "mismatch":         mismatch,
        "customer_country": customer_country,
        "merchant_country": merchant_country,
        "reason":           (
            f"Cross-border transaction ({customer_country}→{merchant_country})"
            if mismatch else "Same-country transaction"
        ),
    })


@tool
def check_channel_risk(channel: str) -> str:
    """
    Return a risk level for the transaction channel.
    API calls and web are riskier than in-person POS.
    """
    risk_map = {
        "pos":    "low",
        "mobile": "medium",
        "web":    "medium",
        "api":    "high",
    }
    risk = risk_map.get(channel.lower(), "medium")
    return json.dumps({
        "risk":    risk,
        "channel": channel,
        "reason":  f"Channel '{channel}' carries {risk} inherent risk",
    })
