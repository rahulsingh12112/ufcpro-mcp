#!/usr/bin/env python3
"""MCP client for the ufcpro-jobs server. Supports a mock driver and AWS Bedrock."""

import sys
import json
import asyncio
import argparse

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def connect():
    params = StdioServerParameters(command=sys.executable, args=["mcp_server.py"])
    return stdio_client(params)


async def discover(session: ClientSession) -> list:
    await session.initialize()
    tools = await session.list_tools()
    return tools.tools


async def run_mock(query: str) -> None:
    async with await connect() as (read, write):
        async with ClientSession(read, write) as session:
            tools = await discover(session)
            print("Discovered tools:", [t.name for t in tools])

            category = "ai" if any(w in query.lower() for w in ("ai", "ml", "mlops")) else "devops"
            print(f"\nMock driver -> calling find_jobs(category={category})")

            result = await session.call_tool("find_jobs", {"category": category})
            payload = _first_text(result)
            data = json.loads(payload) if payload else {}

            jobs = data.get("jobs", [])
            print(f"\nTop {min(5, len(jobs))} of {data.get('count', 0)} jobs:\n")
            for j in jobs[:5]:
                print(f"  - {j['title']}  [{j['company']} | {j['location']}]")
                print(f"    {j['url']}")


async def run_bedrock(query: str, model_id: str) -> None:
    import boto3

    bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

    async with await connect() as (read, write):
        async with ClientSession(read, write) as session:
            tools = await discover(session)
            tool_config = {"tools": [{
                "toolSpec": {
                    "name": t.name,
                    "description": t.description or t.name,
                    "inputSchema": {"json": t.inputSchema},
                }
            } for t in tools]}

            messages = [{"role": "user", "content": [{"text": query}]}]
            resp = bedrock.converse(modelId=model_id, messages=messages, toolConfig=tool_config)

            while resp["stopReason"] == "tool_use":
                out = resp["output"]["message"]
                messages.append(out)
                tool_results = []
                for block in out["content"]:
                    if "toolUse" not in block:
                        continue
                    tu = block["toolUse"]
                    print(f"LLM wants: {tu['name']}({tu['input']})")
                    result = await session.call_tool(tu["name"], tu["input"])
                    tool_results.append({"toolResult": {
                        "toolUseId": tu["toolUseId"],
                        "content": [{"text": _first_text(result) or "{}"}],
                    }})
                messages.append({"role": "user", "content": tool_results})
                resp = bedrock.converse(modelId=model_id, messages=messages, toolConfig=tool_config)

            print("\n" + resp["output"]["message"]["content"][0]["text"])


def _first_text(result) -> str:
    for item in result.content:
        if getattr(item, "type", None) == "text":
            return item.text
    return ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--mock", action="store_true", help="use the mock driver (no AWS)")
    parser.add_argument("--model", default="us.anthropic.claude-haiku-4-5-20251001-v1:0")
    args = parser.parse_args()

    if args.mock:
        asyncio.run(run_mock(args.query))
    else:
        asyncio.run(run_bedrock(args.query, args.model))


if __name__ == "__main__":
    main()
