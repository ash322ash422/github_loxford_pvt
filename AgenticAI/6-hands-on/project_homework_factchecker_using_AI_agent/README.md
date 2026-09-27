# 🧑‍🏫 Homework Fact-Checker Bot

A tiny teaching project that shows the three core pieces of an AI agent:

```
        ┌───────────────────────┐
        │   BRAIN (LLM)         │   gpt-4o-mini via create_agent()
        └──────────┬────────────┘
                    │ decides which tool to call, and when
     ┌──────────────┼───────────────┐
     ▼                              ▼
┌───────────────┐          ┌─────────────────────────┐
│ TOOL 1: SEARCH │          │ TOOL 2: ACTION          │
│ wikipedia_search│         │ save_fact_check_report  │
│ verifies facts  │         │ appends report to file  │
└───────────────┘          └─────────────────────────┘
```

## What it does

1. You give the bot a student's paragraph (`sample_assignment.txt` by default).
2. The **brain** (an OpenAI chat model) reads it and pulls out factual claims
   (dates, names, events).
3. For each claim, the brain calls the **search tool** (`wikipedia_search`)
   to verify it — it doesn't just trust its own memory.
4. It writes a Markdown "Fact-Check Report" (✅ / ❌ / ⚠️ per claim).
5. The brain calls the **action tool** (`save_fact_check_report`), which
   appends that report to the bottom of the assignment file — just like the
   "Google Docs append" step in the original idea, but as a local file so
   the demo needs zero extra credentials.

## Project files

| File                    | Purpose                                              |
|-------------------------|-------------------------------------------------------|
| `app.py`                | Main script — builds the agent and runs it            |
| `tools.py`              | The two tools: `wikipedia_search`, `save_fact_check_report` |
| `sample_assignment.txt` | A demo paragraph with a few planted factual errors     |
| `requirements.txt`      | Pinned package versions                                |

## Setup

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...        # your key
```

## Run it

```bash
python app.py                      # fact-checks sample_assignment.txt
python app.py my_essay.txt         # fact-check any .txt file
python app.py my_essay.pdf         # fact-check a PDF (reads it with pypdf)
```

Open the assignment file afterward — the "🔍 Fact-Check Report" section will
be appended at the bottom.

## The planted errors in `sample_assignment.txt`

So you can confirm the bot is actually checking, not just agreeing:
- The French Revolution began in **1789**, not 1776.
- The Eiffel Tower was built in **1889** for the World's Fair (marking the
  Revolution's **100th** anniversary), not its 50th, and not really "during"
  the revolutionary period itself.
- Napoleon crowning himself Emperor in 1804 is actually **correct** — a good
  example that the bot shouldn't flag everything as wrong.

## How this maps to the original idea

| Original idea                          | This project                                              |
|-----------------------------------------|-------------------------------------------------------------|
| Brain: GPT-4o or Gemini                 | `create_agent(model="gpt-4o-mini", ...)` — swap the model string for `"gpt-4o"` or `"google_genai:gemini-3.5-flash"` |
| Tool 1: Google Search / Wikipedia API   | `wikipedia_search` (no API key needed — great for a classroom) |
| Tool 2: Google Docs append              | `save_fact_check_report` appends to a local file. See "Extending" below for the real Google Docs version. |

## Extending this in class

Good next steps to assign to students, roughly easiest → hardest:

1. **Swap models** — try `gpt-4o` instead of `gpt-4o-mini` and compare report quality.
2. **Add a second search tool** — e.g. a real web search API — and let the
   agent choose which source to use per claim.
3. **Structured output** — use `response_format=` with a Pydantic model so
   the report comes back as a typed list of `{claim, status, explanation}`
   objects instead of free-text Markdown, then render it as HTML.
4. **Real Google Docs** — replace `save_fact_check_report` with a tool that
   calls the Google Docs API (`documents.batchUpdate`) to append text to an
   actual doc. This requires OAuth setup, which is a good "leveling up"
   exercise once students are comfortable with the basics.
5. **Batch mode** — loop over a folder of student submissions and fact-check
   them all in one run.

## Why this is a good teaching example

- It shows the **brain / tools / action** mental model concretely, with only
  two tools — small enough to read end-to-end in one sitting.
- It uses a **prebuilt tool** (`WikipediaQueryRun`) *and* a **custom tool**
  (`save_fact_check_report` via the `@tool` decorator), so students see both
  patterns.
- It's a real daily pain point (checking your own homework) rather than a
  toy example, which makes the "why would I build this" question answer
  itself.
