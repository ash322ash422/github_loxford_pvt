"""
tests/test_graph_integration.py
-----------------------------------
Runs the actual compiled graph end-to-end in rule-based, auto-approve
mode -- no LLM, no network, no human at the keyboard -- using temporary
checkpoint/store databases so tests never touch real project state.

This is the kind of test a real team writes in addition to pure unit
tests: it catches wiring bugs (a node returning the wrong key, an edge
pointing at the wrong node, a tool not being reachable from get_store())
that isolated unit tests can miss.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config
from graph import build_graph

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.sqlite import SqliteStore


def test_full_pipeline_runs_and_produces_a_report(tmp_path):
    config.AUTO_APPROVE_ACTIONS = True
    config.CAMPAIGN_CSV_PATH = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "campaign_data.csv")
    )

    checkpoint_path = str(tmp_path / "test_checkpoints.sqlite")
    store_path = str(tmp_path / "test_memory.sqlite")

    with SqliteSaver.from_conn_string(checkpoint_path) as checkpointer, \
         SqliteStore.from_conn_string(store_path) as store:

        graph = build_graph(checkpointer, store, use_llm=False)
        thread_config = {"configurable": {"thread_id": "pytest-thread"}}

        result = graph.invoke({"csv_path": config.CAMPAIGN_CSV_PATH}, config=thread_config)

        assert "__interrupt__" not in result  # auto-approve should skip all pauses
        assert set(result["decisions"].keys()) == {"Google Search", "Facebook", "Instagram"}
        assert all(v["status"] == "approved" for v in result["applied"].values())
        assert "DECISION SUPPORT REPORT" in result["final_report"]


def test_completed_thread_is_recognized_on_second_invocation(tmp_path):
    """
    Confirms get_state() correctly reports a fully-completed thread
    (next == () with non-empty values) -- the exact check main.py relies
    on to avoid re-running a pipeline that already finished.
    """
    config.AUTO_APPROVE_ACTIONS = True
    config.CAMPAIGN_CSV_PATH = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "campaign_data.csv")
    )
    checkpoint_path = str(tmp_path / "test_checkpoints2.sqlite")
    store_path = str(tmp_path / "test_memory2.sqlite")

    with SqliteSaver.from_conn_string(checkpoint_path) as checkpointer, \
         SqliteStore.from_conn_string(store_path) as store:

        graph = build_graph(checkpointer, store, use_llm=False)
        thread_config = {"configurable": {"thread_id": "pytest-thread-2"}}

        graph.invoke({"csv_path": config.CAMPAIGN_CSV_PATH}, config=thread_config)
        state = graph.get_state(thread_config)

        assert state.values  # not empty -- something ran
        assert state.next == ()  # nothing pending -- fully completed
