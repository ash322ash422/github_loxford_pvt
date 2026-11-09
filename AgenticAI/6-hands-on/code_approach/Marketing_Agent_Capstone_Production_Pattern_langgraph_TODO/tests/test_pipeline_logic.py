"""
tests/test_pipeline_logic.py
-------------------------------
Same principle as the previous version: test every deterministic
function directly, with no LLM/network/API key required. Run with:

    pytest tests/ -v
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from nodes.analytics_node import compute_kpis
from nodes.copilot_node import rule_based_decision


def test_compute_kpis_basic_math():
    rows = [
        {"channel": "Google Search", "impressions": 1000, "clicks": 100, "spend": 200.0, "conversions": 10, "revenue": 500.0},
        {"channel": "Google Search", "impressions": 1000, "clicks": 100, "spend": 200.0, "conversions": 10, "revenue": 500.0},
    ]
    benchmarks = {"Google Search": {"ctr": 0.05, "cpa": 20.0, "roas": 2.0}}
    kpis = compute_kpis(rows, benchmarks)

    result = kpis["Google Search"]
    assert result["ctr"] == 0.1
    assert result["cpc"] == 2.0
    assert result["cpa"] == 20.0
    assert result["roas"] == 2.5


def test_compute_kpis_handles_zero_impressions():
    rows = [{"channel": "Facebook", "impressions": 0, "clicks": 0, "spend": 0.0, "conversions": 0, "revenue": 0.0}]
    kpis = compute_kpis(rows, benchmarks={})
    assert kpis["Facebook"]["ctr"] == 0
    assert kpis["Facebook"]["roas"] == 0


def test_rule_based_decision_reduce_when_losing_money():
    kpis = {"Instagram": {"roas": 0.8, "benchmark_roas": 1.2}}
    decisions = rule_based_decision(kpis)
    assert decisions["Instagram"] == "REDUCE"


def test_rule_based_decision_increase_when_far_above_benchmark():
    kpis = {"Google Search": {"roas": 3.0, "benchmark_roas": 2.0}}
    decisions = rule_based_decision(kpis)
    assert decisions["Google Search"] == "INCREASE"


# NOTE: `apply_recommendation` calls `get_store()`, which only works
# inside a running graph (it reads from LangGraph's execution context).
# That's tested end-to-end in test_graph_integration.py instead.
