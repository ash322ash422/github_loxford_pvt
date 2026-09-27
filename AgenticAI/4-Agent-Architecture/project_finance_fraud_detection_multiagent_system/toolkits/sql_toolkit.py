"""
toolkits/sql_toolkit.py
SQL tools used by the History Agent.
  • get_customer_profile  — fetch customer record
  • get_recent_txns       — fetch last N transactions for a customer
  • get_fraud_rate        — historical fraud rate for this customer
"""

import json
from langchain_core.tools import tool
from utils.db import fetch_one, fetch_all


@tool
def get_customer_profile(customer_id: str) -> str:
    """Fetch the customer profile from the database by customer_id."""
    row = fetch_one(
        "SELECT * FROM customers WHERE customer_id = ?", (customer_id,)
    )
    return json.dumps(row) if row else json.dumps({"error": "customer not found"})


@tool
def get_recent_txns(customer_id: str, limit: int = 10) -> str:
    """Fetch the most recent transactions for a customer (default last 10)."""
    rows = fetch_all(
        """SELECT txn_id, amount, currency, merchant, merchant_country,
                  txn_datetime, channel, is_fraud
           FROM transactions
           WHERE customer_id = ?
           ORDER BY txn_datetime DESC
           LIMIT ?""",
        (customer_id, limit),
    )
    return json.dumps(rows)


@tool
def get_fraud_rate(customer_id: str) -> str:
    """
    Return the historical fraud rate for a customer as a percentage.
    Also returns total transaction count and flagged count.
    """
    row = fetch_one(
        """SELECT COUNT(*) AS total,
                  SUM(is_fraud) AS flagged
           FROM transactions
           WHERE customer_id = ?""",
        (customer_id,),
    )
    if not row or row["total"] == 0:
        return json.dumps({"fraud_rate_pct": 0.0, "total": 0, "flagged": 0})
    rate = round((row["flagged"] or 0) / row["total"] * 100, 2)
    return json.dumps({
        "fraud_rate_pct": rate,
        "total": row["total"],
        "flagged": row["flagged"] or 0,
    })
