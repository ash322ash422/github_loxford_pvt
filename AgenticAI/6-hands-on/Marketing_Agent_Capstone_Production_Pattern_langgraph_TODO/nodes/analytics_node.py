"""
nodes/analytics_node.py
---------------------------
AGENT 2: ANALYTICS AGENT, as a LangGraph node.

Same design decision as before, and it matters just as much in
LangGraph as it did hand-rolled: `compute_kpis` is a plain Python
function the node calls directly -- it is NOT wrapped in @tool and
handed to the model. It needs every raw campaign row as input; making
that an LLM-callable tool would mean the model has to reproduce
(potentially thousands of) rows inside its own tool-call arguments.
Deterministic aggregation stays deterministic, framework or not.

The one real tool here, `lookup_channel_context`, is a small,
LLM-appropriate lookup the model can choose to call per channel before
writing its notes.
"""

from collections import defaultdict

from langchain_core.tools import tool

from state import PipelineState
from logging_config import get_logger

log = get_logger("AnalyticsAgent")

SYSTEM_PROMPT = (
    "You are a marketing analytics agent. You will be given already-computed "
    "KPIs (CTR, CPC, CPA, ROAS) per channel, compared against industry "
    "benchmarks. Your job is to write 2-4 sentences flagging anything "
    "anomalous, concerning, or notably good -- the way a sharp human analyst "
    "would when handing this off to a manager. You may call "
    "lookup_channel_context on any channel if extra qualitative context would "
    "make your notes sharper (e.g. known seasonality or audience quirks)."
)

# Stands in for a lightweight internal knowledge base / retrieval call.
_CHANNEL_KNOWLEDGE = {
    "Google Search": "High-intent traffic; typically the most efficient channel for direct-response conversions.",
    "Facebook":      "Broad reach but often used for awareness; conversion efficiency tends to lag Search.",
    "Instagram":     "Skews younger and more visual; performance is seasonal and campaign-creative dependent.",
}


def compute_kpis(rows: list[dict], benchmarks: dict) -> dict:
    """Deterministic math -- never delegated to the LLM. See module docstring."""
    totals = defaultdict(lambda: {"impressions": 0, "clicks": 0, "spend": 0.0, "conversions": 0, "revenue": 0.0})
    for r in rows:
        t = totals[r["channel"]]
        t["impressions"] += r["impressions"]
        t["clicks"] += r["clicks"]
        t["spend"] += r["spend"]
        t["conversions"] += r["conversions"]
        t["revenue"] += r["revenue"]

    report = {}
    for channel, t in totals.items():
        ctr = t["clicks"] / t["impressions"] if t["impressions"] else 0
        cpc = t["spend"] / t["clicks"] if t["clicks"] else 0
        cpa = t["spend"] / t["conversions"] if t["conversions"] else 0
        roas = t["revenue"] / t["spend"] if t["spend"] else 0
        bench = benchmarks.get(channel, {})
        report[channel] = {
            "ctr": round(ctr, 4), "cpc": round(cpc, 2), "cpa": round(cpa, 2), "roas": round(roas, 2),
            "spend": round(t["spend"], 2), "revenue": round(t["revenue"], 2),
            "benchmark_ctr": bench.get("ctr"), "benchmark_cpa": bench.get("cpa"), "benchmark_roas": bench.get("roas"),
        }
    return report


def _fallback_notes(kpis: dict) -> str:
    flags = []
    for channel, kpi in kpis.items():
        if kpi["roas"] < 1:
            flags.append(f"{channel} is losing money (ROAS {kpi['roas']} < 1.0)")
        elif kpi["benchmark_ctr"] and kpi["ctr"] < kpi["benchmark_ctr"] * 0.7:
            flags.append(f"{channel} CTR ({kpi['ctr']:.2%}) is well below benchmark")
    return "[Rule-based mode] " + ("; ".join(flags) if flags else "No channels breached rule-based thresholds.")


def make_analytics_node(llm=None):
    def analytics_node(state: PipelineState) -> dict:
        log.info("starting run")
        kpis = compute_kpis(state["campaign_data"], state["benchmarks"])
        log.info("computed KPIs", extra={"channel_count": len(kpis)})

        @tool
        def lookup_channel_context(channel: str) -> str:
            """Looks up qualitative context about a marketing channel (audience, seasonality, typical role in the funnel) to help interpret its KPIs."""
            return _CHANNEL_KNOWLEDGE.get(channel, "No additional context available for this channel.")

        if llm is None:
            log.info("running in rule-based mode (no LLM)")
            notes = _fallback_notes(kpis)
        else:
            from tool_loop import run_tool_calling_loop
            tools = [lookup_channel_context]
            notes = run_tool_calling_loop(
                llm.bind_tools(tools), {t.name: t for t in tools}, SYSTEM_PROMPT,
                f"Here are this period's computed KPIs per channel:\n{kpis}",
            )

        return {"kpis": kpis, "analytics_notes": notes}

    return analytics_node
