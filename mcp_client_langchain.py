#!/usr/bin/env python3
"""LangChain MCP client for the ufcpro-jobs server (Bedrock Claude)."""

import sys
import asyncio

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_aws import ChatBedrockConverse

try:
    from langchain.agents import create_agent
except ImportError:
    from langgraph.prebuilt import create_react_agent as create_agent


async def main(query: str) -> None:
    client = MultiServerMCPClient({
        "ufcpro": {
            "command": sys.executable,
            "args": ["mcp_server.py"],
            "transport": "stdio",
        }
    })

    tools = await client.get_tools()

    model = ChatBedrockConverse(
        model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        region_name="us-east-1",
    )

    agent = create_agent(model, tools)
    result = await agent.ainvoke({"messages": query})
    print(result["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "Find top 3 devops jobs in India"))
