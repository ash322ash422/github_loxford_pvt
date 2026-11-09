"""
nodes/data_node.py
---------------------
AGENT 1: DATA AGENT, as a LangGraph node.

Same job and same design as the previous version: gather campaign rows
+ industry benchmarks, using two zero-argument tools. Zero-argument
tools remain the clearest case for genuine LLM tool-calling -- there's
no risk of the model needing to reproduce large data blobs in its own
output, it's purely deciding *whether and when* to call each one.

Tool outputs are captured directly into a local `captured` dict via
closures, exactly as in the previous version -- the model's final text
is only ever used for the human-readable summary, never as the source
of truth for the actual data passed to the next node.
"""

import csv

from langchain_core.tools import tool

from state import PipelineState
from logging_config import get_logger

log = get_logger("DataAgent")

SYSTEM_PROMPT = (
    "You are a data-gathering agent in a marketing analytics pipeline. "
    "Your job is to collect everything the next agent (which computes "
    "marketing KPIs) will need: raw campaign performance data and "
    "industry benchmark figures. Use the tools available to you to "
    "gather both. When you're done, briefly confirm what you gathered."
)


def _read_csv_rows(csv_path: str) -> list[dict]:
    """
    Stands in for a real query, e.g. `SELECT * FROM campaign_daily
    WHERE date >= ...` against a warehouse.
    """
    rows = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "date": row["date"], "channel": row["channel"], "campaign": row["campaign"],
                "impressions": int(row["impressions"]), "clicks": int(row["clicks"]),
                "spend": float(row["spend"]), "conversions": int(row["conversions"]),
                "revenue": float(row["revenue"]),
            })
    return rows


def _benchmark_data() -> dict:
    """
    Stands in for a real external API call, e.g.
    `requests.get("https://api.adbenchmarks.com/v1/kpis").json()`.
    """
    return {
        "Google Search": {"ctr": 0.035, "cpa": 18.0, "roas": 2.0},
        "Facebook":      {"ctr": 0.020, "cpa": 22.0, "roas": 1.5},
        "Instagram":     {"ctr": 0.015, "cpa": 25.0, "roas": 1.2},
    }


def make_data_node(llm=None):
    """
    Returns a node function closed over an optional bound LLM. Passing
    llm=None gives you the deterministic rule-based path (no API key
    needed); passing a real `ChatAnthropic` instance gives you genuine
    tool-calling. This mirrors the `use_llm` flag from the previous
    version, just expressed as a factory function instead of a class
    constructor -- the natural shape for building LangGraph nodes.
    """

    def data_node(state: PipelineState) -> dict:
        log.info("starting run")
        captured: dict = {}

        @tool
        def read_internal_database() -> list[dict]:
            """Reads campaign performance rows (date, channel, impressions, clicks, spend, conversions, revenue) from the internal marketing database."""
            rows = _read_csv_rows(state["csv_path"])
            captured["campaign_data"] = rows
            return rows

        @tool
        def fetch_external_benchmarks() -> dict:
            """Fetches current industry benchmark KPIs (CTR, CPA, ROAS) per marketing channel from an external analytics provider."""
            benchmarks = _benchmark_data()
            captured["benchmarks"] = benchmarks
            return benchmarks

        tools = [read_internal_database, fetch_external_benchmarks]

        if llm is None:
            log.info("running in rule-based mode (no LLM) -- calling tools in fixed order")
            read_internal_database.invoke({})
            fetch_external_benchmarks.invoke({})
            summary = "[Rule-based mode] Loaded campaign data and benchmarks in fixed order."
        else:
            from tool_loop import run_tool_calling_loop
            tools_by_name = {t.name: t for t in tools}
            llm_with_tools = llm.bind_tools(tools)
            summary = run_tool_calling_loop(
                llm_with_tools, tools_by_name, SYSTEM_PROMPT,
                "Gather the campaign data and benchmarks needed for KPI analysis.",
            )

        log.info("run complete", extra={
            "row_count": len(captured.get("campaign_data", [])),
            "channel_count": len(captured.get("benchmarks", {})),
        })

        return {
            "campaign_data": captured.get("campaign_data", []),
            "benchmarks": captured.get("benchmarks", {}),
            "data_agent_summary": summary,
        }

    return data_node
