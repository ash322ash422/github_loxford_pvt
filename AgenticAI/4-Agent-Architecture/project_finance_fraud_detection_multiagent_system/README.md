# 🛡️ Fraud Detection — Multi-Agent System

Real-time transaction fraud detection using three specialist agents
running **in parallel** via LangGraph, then a Decision Agent that
merges all signals into an APPROVE / FLAG / BLOCK verdict.

## Directory Structure

```
fraud_detection/
│
├── app.py                          ← Streamlit UI (entry point)
├── requirements.txt
│
├── database/
│   ├── seed_db.py                  ← Creates & populates fraud.db
│   └── fraud.db                    ← SQLite (created by seed_db.py)
│
├── agents/
│   ├── history_agent.py            ← Customer behaviour analysis
│   ├── fraud_scorer_agent.py       ← ML-style risk signals
│   ├── blacklist_agent.py          ← Deterministic blacklist checks
│   ├── decision_agent.py           ← Merges all signals → verdict
│   └── workflow.py                 ← LangGraph parallel orchestration
│
├── toolkits/
│   ├── sql_toolkit.py              ← get_customer_profile, get_recent_txns, get_fraud_rate
│   ├── fraud_toolkit.py            ← amount_anomaly, velocity, geo_mismatch, channel_risk
│   └── blacklist_toolkit.py        ← check_email, check_merchant, check_ip, check_card
│
└── utils/
    ├── state.py                    ← WorkflowState TypedDict
    └── db.py                       ← SQLite helpers
```

## Setup & Run

```bash
pip install -r requirements.txt
python database/seed_db.py      # once
streamlit run app.py
```

## How Parallelism Works

```python
# LangGraph Send API fires all three agents simultaneously
def orchestrator(state) -> list[Send]:
    return [
        Send("history_agent",      state),
        Send("fraud_scorer_agent", state),
        Send("blacklist_agent",    state),
    ]
```

The Decision Agent sits behind a join point — it only runs after
**all three** parallel agents have returned their results.

## Decision Logic

| Condition                        | Verdict |
|----------------------------------|---------|
| Any blacklist hit                | BLOCK   |
| Composite score > 0.65 or critical signal | BLOCK |
| Composite score 0.35–0.65        | FLAG    |
| Composite score < 0.35           | APPROVE |

Composite = History × 30% + Fraud signals × 50% + Blacklist × 20%

## Why Parallel Agents?

| Sequential (single agent) | Parallel (multi-agent) |
|--------------------------|------------------------|
| History: 400 ms          |                        |
| + Fraud: 600 ms          | All three: ~600 ms     |
| + Blacklist: 200 ms      | (slowest determines it)|
| **Total: ~1,200 ms**     | **Total: ~700 ms**     |
