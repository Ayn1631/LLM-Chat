import sys
import os

# 设置环境变量以确保Python使用UTF-8编码
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

import asyncio
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
# from LLM import llm


async def list_all_tools():
    server_params = StdioServerParameters(
        command="node",
        args=[
            'C:\\Users\\20753\\Documents\\Cline\\MCP\\fetch-mcp\\dist\\index.js'
        ],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_result = await session.list_tools()
            tools = tools_result.tools

            for tool in tools:
                print(f"tool_name：{tool.name}")
                print(f"dis：{tool.description}")
                print(f"args：{tool.inputSchema}")
                print("-" * 40)
            print('-' * 100)
            result = await session.call_tool(
                "search",
                arguments={"query": 'python'}
            )
            print(result.content[0].text)


if __name__ == "__main__":
    res = asyncio.run(list_all_tools())