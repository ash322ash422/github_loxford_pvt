"""utils/state.py — WorkflowState shared across all agents."""

from typing import TypedDict, Optional, Annotated
def merge_dicts(a, b) -> dict:
    return {**(a or {}), **(b or {})}


class Transaction(TypedDict):
    txn_id:           str
    customer_id:      str
    amount:           float
    currency:         str
    merchant:         str
    merchant_country: str
    channel:          str
    customer_email:   Optional[str]
    customer_ip:      Optional[str]
    card_number:      Optional[str]


class WorkflowState(TypedDict):
    # ── input ──────────────────────────────────────────────────────
    transaction: Transaction

    # ── parallel agent outputs ──────────────────────────────────────
    history_result:   Optional[dict]   # from History Agent
    fraud_result:     Optional[dict]   # from Fraud Scorer Agent
    blacklist_result: Optional[dict]   # from Blacklist Agent

    # ── decision agent output ───────────────────────────────────────
    decision:         Optional[str]    # APPROVE / FLAG / BLOCK
    risk_score:       Optional[float]  # 0.0 – 1.0
    reasons:          Optional[list]
    explanation:      Optional[str]

    # ── timing ─────────────────────────────────────────────────────
    timing: Annotated[dict, merge_dicts]  # ← parallel agents safely merge their timings