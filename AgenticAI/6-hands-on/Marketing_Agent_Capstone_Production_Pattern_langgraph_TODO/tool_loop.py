"""
tool_loop.py
--------------
The one shared piece of "agent" machinery every node uses.

COMPARE THIS FILE TO `base_agent.py` IN THE PREVIOUS VERSION of this
project. That file was ~250 lines: hand-building JSON schemas from
Pydantic models, hand-writing the retry-with-backoff decorator, and
manually assembling `tool_result` blocks in the exact shape the raw
Anthropic API expects. Here, LangChain's `ChatAnthropic.bind_tools(...)`
does all of that for us:

  - Tool schemas       -> generated automatically from any @tool-decorated
                           function's type hints / docstring / Pydantic
                           args_schema.
  - Retries w/ backoff -> built into ChatAnthropic via `max_retries=...`
                           (see graph.py where the model is constructed).
  - Message formatting  -> AIMessage / ToolMessage classes handle the
                           exact shape the API needs; we just append
                           messages to a list.
  - Input validation   -> `tool.invoke(args)` validates against the
                           tool's schema automatically and raises if the
                           model sent something malformed.

What's genuinely left for us to write is just the loop itself: call the
model, check if it asked for tools, run them, repeat. That's this
entire file.
"""

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

import config


def run_tool_calling_loop(
    llm_with_tools,
    tools_by_name: dict,
    system_prompt: str,
    user_message: str,
    max_iterations: int = None,
) -> str:
    """
    Runs the standard tool-use loop and returns the model's final text.

    Any tool in `tools_by_name` is free to call LangGraph's `interrupt()`
    internally (see nodes/copilot_node.py's `apply_recommendation`) --
    because this loop executes tools directly, in the same call stack as
    the graph node that invoked it, an interrupt raised here correctly
    pauses the *entire* graph run and can be resumed from main.py exactly
    where it left off. This is the mechanical reason this loop is
    written out explicitly here rather than delegated to a nested
    prebuilt agent, which would execute tools inside its own subgraph.
    """
    max_iterations = max_iterations or config.MAX_TOOL_ITERATIONS
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]

    for _ in range(max_iterations):
        ai_message = llm_with_tools.invoke(messages)
        messages.append(ai_message)

        if not ai_message.tool_calls:
            return ai_message.content

        for call in ai_message.tool_calls:
            tool = tools_by_name[call["name"]]
            try:
                result = tool.invoke(call["args"])
                messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
            except Exception as e:
                # Reported back to the model as an error tool_result so it
                # can see what went wrong and try again, rather than the
                # whole node crashing on a single bad tool call.
                messages.append(ToolMessage(content=f"Error: {e}", tool_call_id=call["id"], status="error"))

    return "[Agent stopped: exceeded maximum tool-call iterations without producing a final answer.]"
