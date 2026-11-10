"""Run a Gemini tool-calling agent against the local MCP demo server."""

import asyncio
import os
import sys
from getpass import getpass
from pathlib import Path

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_SCRIPT_PATH = Path(__file__).with_name("multi_server.py").resolve()

# Optional
# def print_token_usage(result):
#     """Print token usage for Gemini messages in the result."""
#     if result.get("messages"):
#         print("\nGemini token usage:")
#         total_tokens = 0
#         for message in result["messages"]:
#             if isinstance(message, AIMessage) and message.usage_metadata:
#                 # print(f"Message metadata: {message.response_metadata}")  # Model name, finish reason, etc.
#                 usage = message.usage_metadata
#                 total_tokens += usage["total_tokens"]
#                 print(f"  Input: {usage['input_tokens']} | Output: {usage['output_tokens']}")
#         print(f"  Total reported tokens: {total_tokens}")


async def run_classroom_demo(question):
    """Discover MCP tools, run the Gemini agent, and print its tool calls."""
    
    if not SERVER_SCRIPT_PATH.is_file():
        raise SystemExit(f"Place multi_server.py beside this file: {SERVER_SCRIPT_PATH}")

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        api_key = getpass("Gemini API key: ").strip()
    if not api_key:
        raise SystemExit("A Gemini API key is required.")

    model = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
        api_key=api_key,
        vertexai=False,
    )
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_SCRIPT_PATH)],
    )

    # Keep one stdio session open while the agent discovers and calls tools.
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)

            print(f"\nDiscovered {len(tools)} MCP tools:")
            for tool in tools:
                print(f"  {tool.name}: {tool.description}")

            agent = create_agent(
                model=model,
                tools=tools,
                system_prompt=(
                    "You are a classroom assistant. Use the calculator for "
                    "arithmetic and the weather tool for current weather. "
                    "If a weather request lacks coordinates, ask for them. "
                    "If a tool reports an error, explain it without inventing a result. "
                    "For explanations that need neither tool, answer directly."
                ),
            )

            # Gemini chooses the tools and arguments from the user's question.
            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": question}]}
            )

            print("\nTool activity:")
            used_tools = False
            for message in result["messages"]:
                if isinstance(message, AIMessage):
                    for call in message.tool_calls:
                        used_tools = True
                        print(f"  Gemini requested {call['name']}({call['args']})")

                elif isinstance(message, ToolMessage):
                    print(f"  MCP returned: {message.text}")

            if not used_tools:
                print("  No tools called.")

            print(f"\nFinal answer:\n{result['messages'][-1].text}")

            # OPTIONAL: Uncomment to see token usage for Gemini messages in the result.
            # print_token_usage(result)

if __name__ == "__main__":
    question = " ".join(sys.argv[1:]).strip() or input("Ask Gemini: ").strip()
    if not question:
        raise SystemExit("Enter a question to run the demo.")
    asyncio.run(run_classroom_demo(question))


# Example questions to try:
# 1) Explain what a percentage is in one sentence.
# 2) Calculate 12.5 * (40 + 2) ** 2.
# 3) Get the current weather at latitude 28.4595 and longitude 77.0266.
# 4) Get the current temperature at latitude 28.4595 and longitude 77.0266, then use
#    the calculator to convert it from Celsius to Fahrenheit.