# Marketing campaign analysis agent

A small, runnable project that demonstrates the four ideas from the course:

1. **Orchestration of multiple agents**
2. **Combining APIs, databases, and analytics workflows**
3. **AI copilots for decision support**
4. **Mini project: agent for marketing campaign analysis**

No API keys, no internet access, and no frameworks are required to run it.
Everything is plain Python so you can read every line.

## How to run it

**Default mode (no setup at all):**

```bash
cd marketing_agent_project
python main.py
```

That's it. No virtual environment, no `pip install`, no `.env` file. The
project only uses the Python standard library, so it runs identically on
every machine.

You should see each agent print what it's doing, followed by a final
decision-support report recommending which channels to increase, monitor,
or cut.

**Optional: turning on the LLM-powered copilot**

This part needs an API key, so it has its own short setup:

```bash
pip install -r requirements.txt      # installs anthropic + python-dotenv
cp .env.example .env                 # copy the template
# now open .env and replace "your-key-here" with your real OpenAI API key
```

Then in `main.py`, change:

```python
orchestrator = Orchestrator(csv_path="data/campaign_data.csv", use_llm=False)
```

to:

```python
orchestrator = Orchestrator(csv_path="data/campaign_data.csv", use_llm=True)
```

and run `python main.py` again.

## The big idea

Think of this project as a **tiny company**:

| Real company | This project |
|---|---|
| A data analyst who pulls numbers from the database and checks industry reports | `DataAgent` |
| A financial analyst who turns raw numbers into KPIs | `AnalyticsAgent` |
| A marketing manager who reads the KPIs and decides what to do | `CopilotAgent` |
| The team lead who assigns work and passes results between people | `Orchestrator` |

No single agent does everything. Each one has **one job**, and the
orchestrator is the only piece of code that knows about the whole
pipeline.

## Project structure

```
marketing_agent_project/
├── main.py                    <- run this
├── orchestrator.py             <- coordinates the 3 agents
├── data/
│   └── campaign_data.csv       <- the "database"
└── agents/
    ├── data_agent.py            <- Agent 1: fetch data
    ├── analytics_agent.py        <- Agent 2: compute KPIs
    └── copilot_agent.py           <- Agent 3: give a recommendation
```

## Agent 1 — DataAgent (combining an API and a database)

`agents/data_agent.py` fetches from **two different sources**:

- `fetch_campaign_data()` reads `data/campaign_data.csv` — this stands in
  for a real production database.
- `fetch_industry_benchmarks()` returns a hardcoded dictionary — this
  stands in for a real external API call (e.g. an ad platform's
  benchmark endpoint). It's written so a student could swap in a real
  `requests.get(...)` call API

This is the most common real-world pattern: an agent rarely has all the
data it needs in one place. It usually has to combine an internal
database with an external service before anything useful can happen.

## Agent 2 — AnalyticsAgent (the analytics workflow)

`agents/analytics_agent.py` is a **pure function** — no APIs, no files,
just data transformation. It groups the raw rows by channel and computes
four KPIs a real marketer would look at:

- **CTR** (Click Through Rate) = clicks / impressions
- **CPC** (Cost Per Click) = spend / clicks
- **CPA** (Cost Per Acquisition) = spend / conversions
- **ROAS** (Return On Ad Spend) = revenue / spend

This is deliberately kept separate from data-fetching. In a real system,
your analytics logic shouldn't care *where* the numbers came from — it
should be swappable and testable on its own.

## Agent 3 — CopilotAgent (decision support)

`agents/copilot_agent.py` is the "AI copilot." It takes the KPI table and
decides, per channel, whether to `INCREASE`, `MONITOR`, `MAINTAIN`, or
`REDUCE` budget, and explains why in plain English.

It ships with two modes:

- **Rule-based** (default): simple `if` statements compare each KPI to
  its benchmark. Always works, completely free, and easy to trace by
  hand — good for grading and for understanding decision logic before
  adding an LLM into the mix.
- **LLM-powered** (optional, `use_llm=True` in `main.py`): sends the same
  findings to a real Claude model to write a more natural executive
  summary. Requires `pip install openai` and an `OPENAI_API_KEY`
  environment variable. If either is missing, it automatically falls
  back to the rule-based version — the project never crashes.

This mirrors how real AI copilots are built: rules or lightweight models
handle the well-defined math, and a language model is layered on top to
turn structured findings into something a human can act on quickly.

## The Orchestrator (tying it together)

`orchestrator.py` is the only file that knows about all three agents.
It:

1. Calls `DataAgent.run()` and gets back raw data + benchmarks.
2. Passes that straight into `AnalyticsAgent.run()` and gets back KPIs.
3. Checks a simple condition itself — *is every channel losing money?* —
   to decide whether to escalate the report's urgency.
4. Passes the KPIs into `CopilotAgent.run()` and gets back the final
   report.

Notice the orchestrator never touches a CSV file or calculates a KPI
itself. It only **routes work and data between specialists** — that is
the essence of agent orchestration.

## Things to try (exercises)

1. **Change the data.** Edit `data/campaign_data.csv` (or `gen_data.py`
   if you regenerate it) so a different channel is the one losing money.
   Re-run and confirm the copilot's recommendation changes accordingly.
2. **Add a 4th data source.** Add a `fetch_competitor_spend()` method to
   `DataAgent` that returns mock data, and use it in `AnalyticsAgent` to
   flag channels where a competitor is outspending you.
3. **Turn on the LLM copilot.** Set `use_llm=True` in `main.py`, install
   `openai`, and set your API key. Compare the rule-based report to
   the LLM-generated one — what did the LLM add that the rules couldn't?
4. **Add a 4th agent.** Try a `BudgetPlannerAgent` that takes the
   copilot's recommendations and calculates exactly how many dollars to
   move between channels. Wire it into the orchestrator as a 4th step.
5. **Break it on purpose.** Delete a column from the CSV and see which
   agent fails and why. This is a good way to understand where each
   agent's responsibility begins and ends.

## Why this design is "simple but real"

- Every agent is a plain Python class with one public method: `run()`.
  No framework magic to reverse-engineer.
- Data passes between agents as plain Python dictionaries — visible with
  a single `print()`, easy to inspect in a debugger.
- The two "hard" real-world concerns — combining an API with a database,
  and layering an LLM on top of rule-based logic — are both present, but
  isolated so a first-year student can understand one piece at a time.
