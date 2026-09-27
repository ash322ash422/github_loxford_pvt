# 🏦 NL-to-SQL · Multi-Agent Financial Analytics System

A LangGraph-powered system with two specialised agents that work together to answer natural-language questions about a finance database — generating SQL, visualising results, writing reports, and exporting PDFs.

---

## Architecture

```
Streamlit UI
    │
    ▼
LangGraph Workflow
    │
    ├──► Data Analyst Agent
    │         │
    │         └──► SQL Toolkit
    │                   ├── get_schema     → reads DB schema
    │                   ├── execute_sql    → runs SELECT query
    │                   └── data_summary   → factual summary
    │
    └──► Reporting Agent
              │
              ├──► Visualization Toolkit
              │         ├── choose_chart_type  → bar/line/scatter/pie/histogram
              │         └── write_narrative    → 3-5 para report
              │
              └──► PDF Generator
                        └── generate_pdf   → full styled PDF
```

---

## Directory Structure

```
nl2sql/
│
├── app.py                      ← Streamlit UI (entry point)
├── requirements.txt
│
├── database/
│   ├── seed_db.py              ← Populates finance.db
│   └── finance.db              ← SQLite (created by seed_db.py)
│
├── agents/
│   ├── data_analyst.py         ← Data Analyst Agent (3 nodes)
│   ├── reporting_agent.py      ← Reporting Agent (3 nodes)
│   └── workflow.py             ← LangGraph orchestrator
│
├── toolkits/
│   ├── sql_toolkit.py          ← get_schema, execute_sql tools
│   └── viz_toolkit.py          ← choose_chart_type, generate_narrative tools
│
├── graphs/
│   └── charts.py               ← bar / line / scatter / pie / histogram
│
├── reports/
│   └── pdf_report.py           ← PDF builder (ReportLab)
│
└── utils/
    ├── state.py                ← WorkflowState TypedDict
    └── db.py                   ← SQLite helpers
```

---

## Setup

```bash
# 1. Install
pip install -r requirements.txt

# 2. Create and seed the database (run once)
python database/seed_db.py

# 3. Launch
streamlit run app.py
```

Enter your **OpenAI API key** in the sidebar.

---

## LangGraph Node Flow

| # | Node | Agent | Description |
|---|------|-------|-------------|
| 1 | `generate_sql` | Data Analyst | Translates question → SQL |
| 2 | `execute_sql` | SQL Toolkit | Runs query against SQLite |
| 3 | `data_summary` | Data Analyst | Writes a factual 2-3 sentence summary |
| 4 | `choose_chart` | Reporting | Decides best chart type for the data |
| 5 | `write_narrative` | Reporting | Writes a 3-5 paragraph analytical report |
| 6 | `build_pdf` | PDF Generator | Assembles full PDF with chart + report + table |

---

## Database Tables

| Table | Rows | Description |
|-------|------|-------------|
| `customers` | 200 | Name, age, city, credit score, income |
| `loans` | 500 | Type, amount, rate, tenure, status |
| `repayments` | ~5,000 | Payment date, amount, on-time flag |
| `transactions` | 2,000 | Credit/debit by category |
