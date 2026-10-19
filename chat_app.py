#!/usr/bin/env python3
"""Web chat backend: browser <-> Flask <-> Claude (Bedrock) <-> ufcpro-jobs MCP server.

Protected by AWS Cognito (OAuth2 authorization-code flow).
"""

import os
import sys
import secrets
import asyncio
import functools

from flask import (Flask, request, jsonify, send_from_directory,
                   session, redirect, url_for)

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_aws import ChatBedrockConverse

try:
    from langchain.agents import create_agent
except ImportError:
    from langgraph.prebuilt import create_react_agent as create_agent

import auth

HERE = os.path.dirname(os.path.abspath(__file__))
REGION = os.environ.get("AWS_REGION", "us-east-1")
MODEL_ID = os.environ.get("MCP_MODEL", "us.anthropic.claude-haiku-4-5-20251001-v1:0")

app = Flask(__name__, static_folder=HERE, static_url_path="")
app.secret_key = os.environ.get("FLASK_SECRET", secrets.token_hex(32))


def login_required(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return jsonify({"error": "unauthorized", "login": url_for("login")}), 401
        return fn(*args, **kwargs)
    return wrapper


async def ask_agent(query: str) -> str:
    client = MultiServerMCPClient({
        "ufcpro": {
            "command": sys.executable,
            "args": [os.path.join(HERE, "mcp_server.py")],
            "transport": "stdio",
        }
    })
    tools = await client.get_tools()
    model = ChatBedrockConverse(model=MODEL_ID, region_name=REGION)
    agent = create_agent(model, tools)
    result = await agent.ainvoke({"messages": query})
    return result["messages"][-1].content


@app.route("/")
def index():
    return send_from_directory(HERE, "chat.html")


@app.route("/login")
def login():
    return redirect(auth.login_url())


@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return redirect(url_for("index"))
    tokens = auth.exchange_code_for_tokens(code)
    claims = auth.verify_token(tokens["id_token"])
    session["user"] = claims.get("email", claims.get("sub"))
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(auth.logout_url(request.host_url.rstrip("/") + "/"))


@app.route("/me")
def me():
    return jsonify({"user": session.get("user")})


@app.route("/chat", methods=["POST"])
@login_required
def chat():
    query = (request.json or {}).get("message", "").strip()
    if not query:
        return jsonify({"reply": "Please type a message."})
    try:
        reply = asyncio.run(ask_agent(query))
    except Exception as exc:
        reply = f"Error: {exc}"
    return jsonify({"reply": reply})


if __name__ == "__main__":
    print("Chat UI at http://localhost:8800/")
    app.run(host="0.0.0.0", port=8800, debug=False)
