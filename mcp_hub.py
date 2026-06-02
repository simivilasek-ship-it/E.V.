"""MCP Hub (MVP)

Goal: help Jarvis discover and suggest MCP servers for missing capabilities.

This MVP does NOT auto-install arbitrary code by default. It only:
- suggests a known MCP server for a task
- prints an installation plan (manual steps)

A future version can implement sandboxed installation with explicit confirmation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class MCPSuggestion:
    server: str
    description: str
    install_hint: str


# Small curated mapping (safe defaults)
_TASK_HINTS = [
    ("calendar", MCPSuggestion(
        server="google-calendar",
        description="Google Calendar MCP server (requires API credentials).",
        install_hint="Install an official MCP server for Google Calendar (not bundled).",
    )),
    ("slack", MCPSuggestion(
        server="slack",
        description="Slack MCP server (requires SLACK_BOT_TOKEN).",
        install_hint="Enable mcp_slack_enabled in config and set SLACK_BOT_TOKEN in .env.",
    )),
    ("github", MCPSuggestion(
        server="github",
        description="GitHub MCP server (requires GITHUB_TOKEN).",
        install_hint="Enable mcp_github_enabled in config and set GITHUB_TOKEN in .env.",
    )),
]


def suggest(task_text: str) -> Optional[MCPSuggestion]:
    t = (task_text or "").lower()
    for key, sug in _TASK_HINTS:
        if key in t:
            return sug
    return None


def cmd_mcp_suggest(task: str = "") -> str:
    if not task.strip():
        return "Zadej úkol, pro který chceš doporučit MCP server (např. 'calendar')."
    s = suggest(task)
    if not s:
        return "Nenašel jsem známý MCP server pro tento úkol (MVP registry je malý)."
    return (
        f"Doporučený MCP server: {s.server}\n"
        f"Popis: {s.description}\n"
        f"Jak zapnout/instalovat: {s.install_hint}"
    )
