# Automated Student Assignment & Extension Portal

A teaching-oriented example of an **LLM agent built with LangGraph** that reads a
professor's Gmail inbox, classifies student emails, extracts structured info,
applies a written university policy, and leaves a **draft reply** (never sends)
for the professor to review.

## Why this is a good teaching example

It shows the core anatomy of a practical agent:

1. **State** — a typed dict that flows through the graph and accumulates results.
2. **Nodes** — small, single-purpose functions (classify, extract, decide, draft, save).
3. **Structured output** — using Pydantic models + `with_structured_output` so the
   LLM's output is *type-safe*, not a raw string you have to regex.
4. **Conditional edges** — the graph branches based on state (irrelevant emails
   short-circuit before ever hitting the drafting step).
5. **Human-in-the-loop** — the agent never sends email. It writes to Drafts.
   This is the "keep a human in the loop" pattern, not full autonomy.

## Project structure

```
student_agent/
├── config.py              # env vars, model config
├── state.py                # the shared graph state (TypedDict) + Pydantic schemas
├── policy.md                # the university policy the agent must follow (editable, plain text)
├── gmail_service.py         # Gmail API auth + read inbox + create draft
├── nodes/
│   ├── classify.py          # LLM node: what kind of email is this?
│   ├── extract.py           # LLM node: pull student name/roll/course/reason
│   ├── policy_decision.py   # LLM node: apply policy.md to the extracted facts
│   └── draft.py              # LLM node: write the polite reply
├── graph.py                  # wires nodes into a LangGraph StateGraph
├── main.py                   # entry point: poll inbox -> run graph -> write drafts
├── requirements.txt
└── .env.example
```

## How data flows through the graph

```
        START
          │
     ┌────▼─────┐
     │ classify │   -> email_type: extension_request | late_submission
     └────┬─────┘                  | grade_clarification | other
          │
     (conditional edge)
          │
   other ─┴─────────────────► mark_not_relevant ──► END
          │
   relevant
          │
     ┌────▼─────┐
     │ extract  │   -> name, roll_number, course_code, reason
     └────┬─────┘
          │
     ┌────▼─────────┐
     │policy_decision│  -> decision + rationale, grounded in policy.md
     └────┬─────────┘
          │
     ┌────▼─────┐
     │  draft   │   -> subject + body of the reply
     └────┬─────┘
          │
     ┌────▼──────┐
     │ save_draft │  -> writes to Gmail Drafts via Gmail API
     └────┬──────┘
          │
         END
```

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`.
3. Enable the Gmail API in Google Cloud Console, download `credentials.json`
   for a Desktop app OAuth client, and place it in the project root.
   On first run, `gmail_service.py` will open a browser to authorize and will
   cache a `token.json` for subsequent runs.
4. Edit `policy.md` to reflect your actual university/course policy — the
   agent's decisions are only as good as this file.
5. Run:
   ```
   python main.py
   ```
   This polls unread inbox mail, runs each matching email through the graph,
   and leaves a draft in Gmail for the professor to review and send.

## Extending this for a class

Good exercises to give students:
- Swap `policy_decision` to use retrieval (RAG) over a longer, multi-page
  policy document instead of stuffing the whole file in the prompt.
- Add a node that flags emails needing human escalation (e.g. repeated
  extension requests from the same student).
- Add persistence (e.g. a SQLite table) so the agent doesn't re-process
  emails it has already drafted a reply for.
- Replace the "other" branch with a second, smaller graph that handles
  general Q&A using a course FAQ.
