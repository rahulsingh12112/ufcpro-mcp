#!/usr/bin/env python3
"""MCP server exposing ufcpro.in job-search capabilities as tools, resources and prompts."""

import os
import sys
import json
import urllib.parse
import urllib.request

from mcp.server.fastmcp import FastMCP

UFCPRO_BASE = os.environ.get("UFCPRO_BASE", "https://ufcpro.in").rstrip("/")
HTTP_TIMEOUT = 25

mcp = FastMCP("ufcpro-jobs")


def _log(message: str) -> None:
    print(f"[ufcpro-mcp] {message}", file=sys.stderr)


def _get_json(path: str, params: dict | None = None) -> dict:
    url = f"{UFCPRO_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "ufcpro-mcp/1.0"})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        return json.load(resp)


@mcp.tool()
def find_jobs(category: str = "devops") -> dict:
    """Fetch India/remote DevOps or AI roles from the live ufcpro.in job API.

    Args:
        category: "devops" or "ai".
    """
    category = (category or "devops").lower()
    if category not in ("devops", "ai"):
        return {"content": [{"type": "text", "text": "category must be 'devops' or 'ai'"}],
                "isError": True}

    try:
        data = _get_json("/api/jobs", {"category": category})
        jobs = data.get("jobs", [])
        _log(f"find_jobs({category}) -> {len(jobs)} results from {UFCPRO_BASE}")
        return {"count": len(jobs), "jobs": jobs[:25]}
    except Exception as exc:
        return {"content": [{"type": "text", "text": f"ufcpro.in job fetch failed: {exc}"}],
                "isError": True}


@mcp.tool()
def match_jd(jd_text: str, category: str = "devops") -> dict:
    """Score a job description against the resume skills and report gaps.

    Args:
        jd_text: full job description text.
        category: "devops" or "ai".
    """
    category = (category or "devops").lower()
    text = (jd_text or "").lower()
    skills = _RESUME_SKILLS.get("ai" if category == "ai" else "devops", [])

    matched = [s for s in skills if s in text]
    missing = [s for s in skills if s not in text]
    return {
        "match_count": len(matched),
        "matched_skills": matched[:15],
        "resume_has_but_jd_missing": missing[:15],
    }


_RESUME_SKILLS = {
    "devops": ["aws", "kubernetes", "eks", "docker", "helm", "argocd", "terraform",
               "ci/cd", "gitlab", "cloudwatch", "sre", "linux", "python", "iam"],
    "ai": ["rag", "bedrock", "sagemaker", "langchain", "mcp", "llm", "embeddings",
           "vector", "mlflow", "mlops", "aws", "kubernetes", "python"],
}


@mcp.resource("resume://{category}/skills")
def resume_skills(category: str) -> str:
    """Read-only list of resume skills for a category."""
    category = (category or "devops").lower()
    skills = _RESUME_SKILLS.get("ai" if category == "ai" else "devops", [])
    return json.dumps({"category": category, "skills": skills}, indent=2)


@mcp.resource("config://job-sources")
def job_sources() -> str:
    """Public career feeds used by ufcpro.in."""
    return json.dumps({
        "base_url": UFCPRO_BASE,
        "greenhouse": "boards-api.greenhouse.io",
        "ashby": "api.ashbyhq.com",
        "remotive": "remotive.com/api",
        "himalayas": "himalayas.app/jobs/api",
        "adzuna": "api.adzuna.com",
    }, indent=2)


@mcp.prompt()
def outreach_email(company: str, role: str, your_name: str = "Rahul") -> str:
    """Template to draft a recruiter outreach email."""
    return (
        f"You are {your_name}, a job candidate. Write a short, professional, "
        f"personalized outreach email for the '{role}' role at {company}. "
        f"Keep it under 120 words, not spammy, with a clear call to action."
    )


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    if transport == "http":
        _log("starting on streamable-http transport")
        mcp.run(transport="streamable-http")
    else:
        _log("starting on stdio transport")
        mcp.run()
