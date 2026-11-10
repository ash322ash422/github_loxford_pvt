"""Use Gemini to select and call tools on the MarketIntel MCP server."""

import asyncio
import os
import sys
from getpass import getpass
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession
from mcp.client.sse import sse_client

SERVER_URL = "http://127.0.0.1:8000/sse"


async def run_demo(question: str, api_key: str) -> None:
    """Discover MarketIntel tools, let Gemini choose, and print the answer."""
    model = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
        api_key=api_key,
        vertexai=False,
    )

    # Connect to the server already running in the other terminal.
    async with sse_client(SERVER_URL) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            print("Discovered MCP tools:", ", ".join(tool.name for tool in tools))

            agent = create_agent(
                model=model,
                tools=tools,
                system_prompt=(
                    "You are a market research assistant. Use MarketIntel tools "
                    "when the user requests company research, competitors, products, "
                    "pricing, or recent news. Use up to three search results per tool "
                    "call. Include source URLs from the tool results for factual claims. "
                    "If the tool fails or the evidence is insufficient, say so. "
                    "Answer general conceptual questions directly."
                ),
            )

            # LangChain sends tool requests to MCP and returns the results to Gemini.
            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": question}]}
            )

    print("\nTool requests:")
    tool_calls = [
        call
        for message in result["messages"]
        if isinstance(message, AIMessage)
        for call in message.tool_calls
    ]
    for call in tool_calls:
        print(f"  {call['name']}({call['args']})")
    if not tool_calls:
        print("  No tools requested.")

    print(f"\nGemini's answer:\n{result['messages'][-1].text}")


def main() -> None:
    """Read the question and Gemini key, then run one agent turn."""
    question = " ".join(sys.argv[1:]).strip() or input("Ask Gemini: ").strip()
    if not question:
        raise SystemExit("Enter a question to run the demo.")

    load_dotenv(Path(__file__).with_name(".env"))
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        api_key = getpass("Gemini API key: ").strip()
    if not api_key:
        raise SystemExit("A Gemini API key is required.")

    asyncio.run(run_demo(question, api_key))


if __name__ == "__main__":
    main()

