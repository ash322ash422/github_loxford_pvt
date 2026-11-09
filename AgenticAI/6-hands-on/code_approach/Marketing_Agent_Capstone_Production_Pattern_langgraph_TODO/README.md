# Marketing campaign analysis agent -- LangGraph version

The same three-agent pipeline, rebuilt on **LangGraph** instead of a
hand-rolled orchestrator. Same task, same tools, same human-approval
gate -- but every piece of infrastructure we wrote by hand in the
previous version now comes from the framework.

## Quickstart

```bash
pip install -r requirements.txt

# Rule-based mode -- no API key needed
python main.py

# Real LLM + tool-calling modeV
cp .env.example .env        # paste a real ANTHROPIC_API_KEY into it
python main.py --use-llm

# Skip the human-approval prompt (useful for demos/CI)
python main.py --use-llm --auto-approve

# Run tests
pytest tests/ -v
```

**Try this to see the framework's resumability for real:** run
`python main.py` (no `--auto-approve`), and as soon as the first
`[HUMAN APPROVAL REQUIRED]` prompt appears, hit Ctrl+C. Then run
`python main.py` again. You'll see it resume from that exact paused
approval -- DataAgent and AnalyticsAgent do not re-run.

## What maps to what

This is the real value of the exercise: everything we hand-built in
the previous version has a direct LangGraph equivalent.

| Hand-rolled version | LangGraph version |
|---|---|
| `base_agent.py`'s ~250-line `run_agentic_loop` (manual JSON schemas, manual retry decorator, manual tool_result blocks) | `tool_loop.py`'s ~25-line loop, on top of `ChatAnthropic.bind_tools(...)` which generates schemas and handles retries for us |
| `agents/tool_schemas.py` Pydantic models, wired in by hand | `@tool`-decorated functions -- LangChain derives the schema from the function's type hints and docstring automatically |
| Hand-rolled `checkpoints/*.json` + `if completed_stage == ...: skip` logic in `orchestrator.py` | `SqliteSaver` checkpointer, wired into `graph.compile(checkpointer=...)` -- persists after every node for free |
| Hand-rolled `memory/*.json` per agent | `SqliteStore`, accessed via `get_store()` -- LangGraph's dedicated concept for cross-thread, long-term memory (see below) |
| Blocking `input()` call inside `CopilotAgent.apply_recommendation` | `interrupt(...)` inside the same tool -- pauses the *entire graph*, persists exactly where it paused, and can be resumed by a completely different process later via `Command(resume=...)` |
| `tenacity` retry decorator around the raw Anthropic SDK call | `ChatAnthropic(max_retries=...)` -- built in |
| Orchestrator class calling `.run()` on each agent in sequence | `StateGraph` with `add_edge(...)` between nodes |

## Two kinds of persistence -- a distinction LangGraph makes explicit

The previous version blurred "pipeline progress" and "agent memory"
into similarly-shaped JSON files. LangGraph splits them into two
different concepts, and building this version makes the difference
concrete:

- **Checkpointer** (`checkpoints.sqlite`) -- state for *this run*
  (which thread, which stage). Scoped to a `thread_id`. This is what
  makes a paused or crashed run resumable.
- **Store** (`agent_memory.sqlite`) -- long-term facts an agent should
  remember *across* runs, retrievable from any thread. CopilotAgent's
  past recommendations live here (`nodes/copilot_node.py`,
  `MEMORY_NAMESPACE`).

Running `python main.py --reset` wipes the checkpointer (start the
pipeline over) but deliberately leaves the store untouched -- exactly
like resetting a workflow shouldn't erase what an agent has learned
over time.

## Project structure

```
langgraph_project/
├── main.py               <- CLI entry point; owns the interrupt/resume loop
├── graph.py               <- builds and compiles the StateGraph
├── state.py                <- the PipelineState TypedDict shared by every node
├── tool_loop.py              <- the one shared tool-calling loop every node uses
├── config.py
├── logging_config.py
├── data/campaign_data.csv
├── nodes/
│   ├── data_node.py          <- Agent 1
│   ├── analytics_node.py       <- Agent 2
│   ├── escalation_node.py        <- orchestrator-level check (not an agent)
│   └── copilot_node.py             <- Agent 3, with the interrupt()-based approval gate
└── tests/
    ├── test_pipeline_logic.py     <- unit tests, no LLM/graph needed
    └── test_graph_integration.py    <- runs the real compiled graph end-to-end
```

## Design decisions carried over unchanged

Two of the most important lessons from the previous version still
apply exactly as written, framework or not -- worth re-reading the
docstrings at the top of these two files:

- **`compute_kpis` (`nodes/analytics_node.py`) is a plain function, not
  a tool.** Deterministic math shouldn't be reproduced by a model, in
  any framework.
- **`rule_based_decision` (`nodes/copilot_node.py`) is a plain
  function, not a tool.** A budget decision needs a consistent,
  auditable answer; the LLM's job is explaining it, not making it.

## Exercises

1. **Make `data_node`'s two tools run concurrently.** They don't depend
   on each other. Look into LangGraph's support for parallel node
   execution (fan-out/fan-in with multiple edges from one node) as an
   alternative to running them sequentially inside one node.
2. **Swap `create_react_agent` in for `tool_loop.py`.** For
   `data_node` and `analytics_node` (neither needs `interrupt()`), try
   replacing the manual loop with LangGraph's prebuilt
   `create_react_agent(...)`. Measure how many lines you get to delete.
   (`copilot_node` should probably keep the manual loop -- see the
   comment in `tool_loop.py` about why nested prebuilt agents complicate
   interrupt propagation.)
3. **Add LangSmith tracing.** Set the `LANGCHAIN_TRACING_V2` and
   `LANGCHAIN_API_KEY` environment variables and re-run `--use-llm`
   mode. Compare what you can see in the trace UI to what our
   hand-rolled JSON logs showed.
4. **Give the escalation check real branching.** Right now
   `escalation_node` always proceeds to `copilot_agent`. Use
   `add_conditional_edges` so that when every channel is losing money,
   the graph routes to a (new) `emergency_review_node` instead of the
   normal copilot flow.
5. **Run two threads concurrently.** Kick off `--thread-id runA` and
   `--thread-id runB` and confirm they're fully independent pipelines
   sharing the same long-term memory store but not each other's
   pipeline state.
