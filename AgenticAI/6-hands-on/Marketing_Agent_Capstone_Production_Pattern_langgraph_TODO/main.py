"""
main.py
--------
Entry point for the LangGraph version of the pipeline.

Usage:
    python main.py                    # rule-based mode, no API key needed
    python main.py --use-llm          # real Claude tool-calling in every node
    python main.py --reset            # wipe pipeline checkpoint state, start clean
    python main.py --auto-approve     # skip the human-approval prompt (CI/demos)

Run it, kill it (Ctrl+C) right after an "[HUMAN APPROVAL REQUIRED]"
prompt appears, then run `python main.py` again (no flags) -- you'll
see the pipeline resume from exactly that paused approval instead of
re-running DataAgent and AnalyticsAgent from scratch. That's
LangGraph's checkpointer doing, for free, what the previous version of
this project's `orchestrator.py` did by hand with a JSON file.
"""

import argparse
import os

import config
from graph import build_graph
from logging_config import get_logger

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.sqlite import SqliteStore
from langgraph.types import Command

log = get_logger("main")


def parse_args():
    parser = argparse.ArgumentParser(description="Marketing campaign analysis pipeline (LangGraph)")
    parser.add_argument("--use-llm", action="store_true", help="Use real Claude tool-calling instead of rule-based fallbacks")
    parser.add_argument("--reset", action="store_true", help="Wipe pipeline checkpoint state and start this thread from stage 1")
    parser.add_argument("--auto-approve", action="store_true", help="Automatically approve any write action instead of prompting a human")
    parser.add_argument("--thread-id", default="main", help="Pipeline run identifier -- separate thread-ids run fully independent pipelines")
    return parser.parse_args()


def handle_approval_prompt(interrupt_payload: dict) -> bool:
    print(f"\n[HUMAN APPROVAL REQUIRED] {interrupt_payload['channel']}: recommended action = {interrupt_payload['action']}")
    print(f"  Rationale: {interrupt_payload['rationale']}")
    try:
        answer = input("  Approve this action? [y/N]: ").strip().lower()
    except EOFError:
        log.warning("no interactive input available; defaulting to NOT approved")
        return False
    return answer == "y"


def run_pipeline_to_completion(graph, thread_config: dict, initial_state: dict | None):
    """
    Runs the graph, transparently handling any number of approval
    interrupts along the way by resuming with `Command(resume=...)`
    until the graph reaches END.
    """
    result = graph.invoke(initial_state, config=thread_config)
    while "__interrupt__" in result:
        interrupt_obj = result["__interrupt__"][0]
        approved = handle_approval_prompt(interrupt_obj.value)
        result = graph.invoke(Command(resume=approved), config=thread_config)
    return result


if __name__ == "__main__":
    args = parse_args()

    if args.auto_approve:
        os.environ["AUTO_APPROVE_ACTIONS"] = "true"
        config.AUTO_APPROVE_ACTIONS = True

    if args.reset and os.path.exists(config.CHECKPOINT_DB_PATH):
        os.remove(config.CHECKPOINT_DB_PATH)
        log.info("checkpoint database reset -- agent long-term memory (agent_memory.sqlite) was NOT touched")

    thread_config = {"configurable": {"thread_id": args.thread_id}}

    with SqliteSaver.from_conn_string(config.CHECKPOINT_DB_PATH) as checkpointer, \
         SqliteStore.from_conn_string(config.STORE_DB_PATH) as store:

        graph = build_graph(checkpointer, store, use_llm=args.use_llm)

        existing = graph.get_state(thread_config)

        if not existing.values:
            log.info("no existing checkpoint for this thread -- starting fresh", extra={"thread_id": args.thread_id})
            result = run_pipeline_to_completion(
                graph, thread_config,
                {"csv_path": config.CAMPAIGN_CSV_PATH},
            )
        elif not existing.next:
            log.info("this thread already ran to completion -- showing its stored result "
                      "(use --thread-id <new-id> or --reset to run again)")
            result = existing.values
        else:
            pending_interrupts = any(t.interrupts for t in existing.tasks)
            if pending_interrupts:
                log.info("resuming a run that was paused on a human-approval request")
            else:
                log.info("resuming a run that stopped before completing (e.g. a crash) -- "
                         "continuing from the last completed step, not from scratch")
            result = run_pipeline_to_completion(graph, thread_config, None)

        print("\n" + result["final_report"])
        print(
            "(Tip: checkpoints.sqlite holds this run's resumable pipeline state; "
            "agent_memory.sqlite holds CopilotAgent's long-term memory across runs. "
            "Try --thread-id demo2 for a fully independent parallel run.)"
        )
