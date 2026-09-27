# 🏦 NL-to-SQL + Report Generator

Ask questions about a SQLite lending database in plain English. The system generates SQL, runs it, visualises the results, writes an AI summary, and exports a PDF report.

## Directory Structure

```
nl2sql/
│
├── app.py                  ← Streamlit UI (entry point)
│
├── database/
│   ├── seed_db.py          ← Creates & populates lending.db
│   └── lending.db          ← SQLite DB (created by seed_db.py)
│
├── utils/
│   ├── agent.py            ← LangGraph pipeline (NL → SQL → Execute → Summarise)
│   └── db.py               ← Schema inspector + query runner
│
├── graphs/
│   └── charts.py           ← Auto chart selection from DataFrame
│
├── reports/
│   └── pdf_report.py       ← PDF generation with ReportLab
│
└── requirements.txt
```

## Tech Stack

| Component | Library |
|-----------|---------|
| UI | Streamlit |
| AI pipeline | LangGraph + LangChain |
| LLM | OpenAI GPT-4o-mini |
| Database | SQLite3 |
| Charts | Matplotlib |
| PDF | ReportLab |

## Setup & Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Seed the database (run once)
python database/seed_db.py

# 3. Launch the app
streamlit run app.py
```

Enter your **OpenAI API key** in the sidebar when the app opens.

## How It Works

```
User question (natural language)
        │
        ▼
[LangGraph Node 1] generate_sql
  LLM reads the schema and writes a SELECT query
        │
        ▼
[LangGraph Node 2] execute_sql
  Query runs against lending.db → returns a DataFrame
        │
        ▼
[LangGraph Node 3] summarise
  LLM reads the first 10 rows and writes a plain-English summary
        │
        ▼
Streamlit renders:
  • SQL code block
  • AI summary
  • Interactive data table
  • Auto-selected chart
  • PDF download button
```

## Sample Questions

- "How many loans are active, closed, and defaulted?"
- "What is the average loan amount by loan type?"
- "Which city has the highest number of defaulted loans?"
- "Show total repayments collected per month in 2023"
- "List the top 10 customers by total loan amount"
- "What is the average credit score of customers who defaulted?"
