# multi_client.py

"""MCP client: launches multi_server.py over stdio, lists tools, calls both."""

import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_classroom_demo():
    # Define absolute path to the multi-tool server file
    server_script_path = os.path.abspath("multi_server.py")
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script_path],
        env=os.environ.copy()
    )

    print("Launching and connecting to Multi-Tool Server...")
    
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("Successfully Connected! Handshake completed.\n")

            # 1. Discover all tools hosted on the server
            tools_response = await session.list_tools()
            print("=========================================")
            print(f"DISCOVERED {len(tools_response.tools)} TOOLS ON THIS SERVER:")
            print("=========================================")
            for tool in tools_response.tools:
                print(f"🛠️ Tool Name: {tool.name}")
                print(f"   Description: {tool.description}\n")

            print("=========================================")
            print("RUNNING DEMO EXECUTION ACTIONS:")
            print("=========================================\n")

            # 2. Call Tool 1: The Precision Calculator
            calc_args = {"expression": "12.5 * (40 + 2) ** 2"}
            print(f"👉 Simulating LLM Request: Calling 'calculate_expression' with {calc_args}")
            
            calc_result = await session.call_tool("calculate_expression", arguments=calc_args)
            print(f"📥 Response from Server: {calc_result.content[0].text}\n")

            # 3. Call Tool 2: The Live Weather Fetcher
            # Coordinates for Gurugram, India
            weather_args = {"latitude": 28.4595, "longitude": 77.0266}
            print(f"👉 Simulating LLM Request: Calling 'get_live_weather' with {weather_args}")
            
            weather_result = await session.call_tool("get_live_weather", arguments=weather_args)
            print(f"📥 Response from Server: {weather_result.content[0].text}\n")

if __name__ == "__main__":
    asyncio.run(run_classroom_demo())
