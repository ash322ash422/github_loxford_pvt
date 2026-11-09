"""
nodes/copilot_node.py
-------------------------
AGENT 3: COPILOT AGENT, as a LangGraph node.

Two things are genuinely new here compared to the hand-rolled version,
both native LangGraph concepts:

1. LONG-TERM MEMORY VIA STORE, NOT A JSON FILE.
   The hand-rolled version kept a JSON file per agent for memory.
   LangGraph draws an explicit line between two kinds of persistence:
     - the CHECKPOINTER persists this run's pipeline state (which stage
       it's on) -- see graph.py. That's per-thread/per-run state.
     - the STORE persists facts an agent should remember ACROSS runs --
       here, CopilotAgent's past recommendations. That's long-term,
       cross-thread memory, retrievable by namespace/key from any future
       run. `get_store()` returns whichever store the graph was compiled
       with (see graph.py) -- nodes and tools don't need it passed in
       explicitly.

2. A REAL APPROVAL GATE VIA `interrupt()`, NOT A BLOCKING `input()`.
   `apply_recommendation` is the one tool in this project that WRITES
   something (stands in for pushing a real budget change to an ads
   platform). Calling `interrupt(...)` inside it pauses the ENTIRE graph
   run -- not just this node -- and persists exactly where it paused via
   the checkpointer. `main.py` catches that pause, shows the human a
   real approval prompt, and resumes the exact same run with
   `graph.invoke(Command(resume=answer), config)`. This is the
   documented, supported way to do human-in-the-loop in LangGraph, and
   it's strictly more robust than a blocking `input()` mid-function: the
   process can restart entirely between the pause and the resume (e.g.
   a real approval arriving from a Slack button click hours later) and
   the graph will still pick up exactly where it left off.
"""

from langchain_core.tools import tool
from langgraph.types import interrupt

from langgraph.config import get_store

import config
from state import PipelineState
from logging_config import get_logger

log = get_logger("CopilotAgent")

SYSTEM_PROMPT = (
    "You are a marketing decision-support copilot. You will be given KPIs, "
    "analyst notes, and a REQUIRED action per channel that has already been "
    "decided by a deterministic rules engine (do not change these actions). "
    "Your job: for EACH channel, call apply_recommendation exactly once with "
    "that channel's required action and a one-to-two sentence rationale "
    "grounded in the KPIs and notes you were given. You may call "
    "get_past_recommendations first if recent history would sharpen your "
    "rationale (e.g. to note that a decision changed from last time). "
    "After all channels are submitted, write a 3-5 sentence executive summary."
)

MEMORY_NAMESPACE = ("copilot_agent", "recommendations")  # store namespace for long-term memory


def rule_based_decision(kpis: dict) -> dict:
    """Deterministic decision engine -- never delegated to the LLM. See module docstring in the previous project version for the full rationale."""
    decisions = {}
    for channel, kpi in kpis.items():
        bench_roas = kpi.get("benchmark_roas") or 1.0
        if kpi["roas"] < 1:
            decisions[channel] = "REDUCE"
        elif kpi["roas"] >= bench_roas * 1.2:
            decisions[channel] = "INCREASE"
        elif kpi["roas"] < bench_roas * 0.8:
            decisions[channel] = "MONITOR"
        else:
            decisions[channel] = "MAINTAIN"
    return decisions


@tool
def get_past_recommendations(limit: int = 3) -> list[dict]:
    """Retrieves this agent's most recent past recommendations from long-term memory, useful for noting changes over time."""
    store = get_store()
    items = store.search(MEMORY_NAMESPACE, limit=limit)
    return [item.value for item in items]


@tool
def apply_recommendation(channel: str, action: str, rationale: str) -> dict:
    """Submits a budget recommendation for one channel. This is a WRITE action and requires human approval before it takes effect."""
    if config.AUTO_APPROVE_ACTIONS:
        approved = True
        log.info("auto-approved (AUTO_APPROVE_ACTIONS=true)", extra={"channel": channel})
    else:
        # Pauses the ENTIRE graph run here. `main.py` is what actually
        # shows this to a human and supplies the resume value.
        approved = interrupt({
            "kind": "approval_request",
            "channel": channel, "action": action, "rationale": rationale,
        })

    status = "approved" if approved else "rejected_by_human_reviewer"
    record = {"channel": channel, "action": action, "rationale": rationale, "approved": approved, "status": status}

    store = get_store()
    store.put(MEMORY_NAMESPACE, f"{channel}:{action}", record)

    return record


def _fallback_summary(decisions: dict) -> tuple[str, dict]:
    applied = {}
    for channel, action in decisions.items():
        result = apply_recommendation.invoke({
            "channel": channel, "action": action,
            "rationale": f"[Rule-based mode] ROAS-vs-benchmark rule selected {action}.",
        })
        applied[channel] = result
    summary = "[Rule-based mode] Recommendations were generated by the rules engine with templated rationale (no LLM configured)."
    return summary, applied


def make_copilot_node(llm=None):
    def copilot_node(state: PipelineState) -> dict:
        log.info("starting run")
        kpis = state["kpis"]
        notes = state["analytics_notes"]

        decisions = rule_based_decision(kpis)
        log.info("computed required actions", extra={"decisions": decisions})

        tools = [get_past_recommendations, apply_recommendation]

        if llm is None:
            log.info("running in rule-based mode (no LLM)")
            summary, applied = _fallback_summary(decisions)
        else:
            from tool_loop import run_tool_calling_loop
            user_message = (
                f"KPIs: {kpis}\n\nAnalyst notes: {notes}\n\n"
                f"Required actions (already decided, do not change): {decisions}\n\n"
                "Submit each channel's required action via apply_recommendation, "
                "then write your executive summary."
            )
            summary = run_tool_calling_loop(
                llm.bind_tools(tools), {t.name: t for t in tools}, SYSTEM_PROMPT, user_message,
            )
            # apply_recommendation writes each result to the store as it's
            # called; re-read the freshest ones so the final report reflects
            # exactly what was approved/rejected this run.
            store = get_store()
            applied = {}
            for channel, action in decisions.items():
                item = store.get(MEMORY_NAMESPACE, f"{channel}:{action}")
                if item:
                    applied[channel] = item.value

        header = "MARKETING CAMPAIGN ANALYSIS - DECISION SUPPORT REPORT\n" + "=" * 55
        lines = [f"- {ch}: {act}  [{applied.get(ch, {}).get('status', 'not submitted')}]" for ch, act in decisions.items()]
        report = f"{header}\n\n{summary}\n\nDecisions by channel:\n" + "\n".join(lines) + "\n"
        if state.get("escalate"):
            report = "*** URGENT REVIEW NEEDED: every channel is losing money ***\n\n" + report

        return {"decisions": decisions, "applied": applied, "copilot_summary": summary, "final_report": report}

    return copilot_node
