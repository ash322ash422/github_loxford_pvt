"""Inspect the MarketIntel server or call one research tool over MCP."""

import argparse
import asyncio
import json

from fastmcp import Client
from fastmcp.client.transports import SSETransport

SERVER_URL = "http://127.0.0.1:8000/sse"


async def inspect_server(client: Client) -> None:
    """Show tools, read a resource, and render a prompt without Tavily."""
    identity = await client.call_tool("server_identity")
    print(f"Connected to: {identity.data['server']}")

    print("\nTOOLS")
    for tool in await client.list_tools():
        print(f"  {tool.name}")

    print("\nRESOURCE  resource://market/topics")
    for item in await client.read_resource("resource://market/topics"):
        print(item.text)

    print("\nPROMPT  competitor_analysis_prompt")
    prompt = await client.get_prompt(
        "competitor_analysis_prompt", {"company": "Zoho", "region": "India"}
    )
    for message in prompt.messages:
        print(message.content.text)


async def run_demo(args: argparse.Namespace) -> None:
    """Connect to the server and run inspection or one live search."""

    async with Client(SSETransport(SERVER_URL)) as client:
        if args.company is None:
            await inspect_server(client)
            return

        tool = "list_competitors" if args.competitors else "company_overview"
        arguments = {"name": args.company, "region": args.region, "max_results": 2}
        print(f"Calling {tool} with {arguments}", flush=True)
        result = await client.call_tool(tool, arguments)
        data = result.data
        print(f"\nSearch query: {data['query_used']}")
        print(f"\nTavily answer: {data['answer'] or 'No summary returned.'}")
        print("\nSources:")
        for source in data["results"]:
            print(f"  {source['title']}\n  {source['url']}")

        if args.json:
            print("\nFull tool result:")
            print(json.dumps(data, indent=2, ensure_ascii=False))


def main() -> None:
    """Parse command-line options and start the demo."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("company", nargs="?", help="Company to search for")
    parser.add_argument("--region", help="Optional region, such as India")
    parser.add_argument("--competitors", action="store_true", help="Call list_competitors")
    parser.add_argument("--json", action="store_true", help="Show the complete tool response")
    asyncio.run(run_demo(parser.parse_args()))


if __name__ == "__main__":
    main()

