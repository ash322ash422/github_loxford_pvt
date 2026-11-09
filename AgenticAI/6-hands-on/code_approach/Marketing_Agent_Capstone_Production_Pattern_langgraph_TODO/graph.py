"""
graph.py
---------
Builds the pipeline as a LangGraph `StateGraph` and compiles it with:

  - a CHECKPOINTER (`SqliteSaver`)     -> persists pipeline run state to
                                          disk after every node, giving
                                          resumability for free. This is
                                          the direct replacement for the
                                          hand-rolled `checkpoints/*.json`
                                          file + `if stage == ...: skip`
                                          logic in the previous version's
                                          `orchestrator.py`.
  - a STORE (`SqliteStore`)            -> persists CopilotAgent's
                                          long-term memory (past
                                          recommendations) across runs.
                                          Direct replacement for the
                                          hand-rolled `memory/*.json`
                                          files.

The pipeline shape is UNCHANGED from every previous version of this
project -- still sequential:

    data_agent -> analytics_agent -> escalation_check -> copilot_agent

What's different is that LangGraph now owns resumability, long-term
memory, and human-in-the-loop pausing, instead of us hand-rolling each
of those.
"""

from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic

import config
from state import PipelineState
from nodes.data_node import make_data_node
from nodes.analytics_node import make_analytics_node
from nodes.escalation_node import escalation_node
from nodes.copilot_node import make_copilot_node


def build_llm():
    """
    Returns a tool-calling-ready Claude model, or None for rule-based
    mode. Retries with backoff are handled by `max_retries` here --
    the built-in equivalent of the `tenacity` decorator the hand-rolled
    version needed to write itself.
    """
    return ChatAnthropic(
        model=config.MODEL_NAME,
        max_tokens=config.MAX_OUTPUT_TOKENS,
        max_retries=config.LLM_MAX_RETRIES,
        timeout=30,
    )


def build_graph(checkpointer, store, use_llm: bool = False):
    llm = None
    if use_llm:
        if not config.ANTHROPIC_API_KEY:
            print("[warning] --use-llm was set but no ANTHROPIC_API_KEY was found; "
                  "falling back to rule-based mode for every agent.")
        else:
            llm = build_llm()

    graph = StateGraph(PipelineState)
    graph.add_node("data_agent", make_data_node(llm))
    graph.add_node("analytics_agent", make_analytics_node(llm))
    graph.add_node("escalation_check", escalation_node)
    graph.add_node("copilot_agent", make_copilot_node(llm))

    graph.add_edge(START, "data_agent")
    graph.add_edge("data_agent", "analytics_agent")
    graph.add_edge("analytics_agent", "escalation_check")
    graph.add_edge("escalation_check", "copilot_agent")
    graph.add_edge("copilot_agent", END)

    return graph.compile(checkpointer=checkpointer, store=store)
