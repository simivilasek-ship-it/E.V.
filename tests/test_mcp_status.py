"""Status MCP serverů — ready vs. chybějící klíče."""

from __future__ import annotations

import pytest

from src.api.routers.settings import collect_mcp_status


def _cfg(**overrides):
    base = {
        "mcp_filesystem_enabled": True,
        "mcp_git_enabled": True,
        "mcp_memory_enabled": True,
        "mcp_fetch_enabled": True,
        "mcp_brave_enabled": False,
        "mcp_playwright_enabled": True,
        "mcp_github_enabled": True,
        "mcp_youtube_transcript_enabled": True,
        "mcp_google_maps_enabled": True,
        "mcp_slack_enabled": True,
        "mcp_sequential_thinking_enabled": True,
        "mcp_puppeteer_enabled": True,
        "mcp_computer_control_enabled": True,
        "mcp_time_enabled": True,
    }
    base.update(overrides)
    return base


@pytest.mark.unit
def test_missing_api_keys_are_not_counted_as_enabled(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    monkeypatch.setattr("config.github_token_from_gh", lambda: "")
    monkeypatch.setattr("src.api.routers.settings.shutil.which", lambda cmd: "/usr/bin/" + cmd)

    servers, summary = collect_mcp_status(_cfg())
    by_name = {s["name"]: s for s in servers}

    assert by_name["github"]["enabled"] is True
    assert by_name["github"]["ready"] is False
    assert "GITHUB_TOKEN" in by_name["github"]["hint"]
    assert by_name["google-maps"]["ready"] is False
    assert by_name["slack"]["ready"] is False
    assert by_name["filesystem"]["ready"] is True
    # github/maps/slack chybí klíč → nepočítají se do enabled_total
    assert summary["ready_total"] == summary["enabled_total"]
    assert summary["score"] == 100


@pytest.mark.unit
def test_github_ready_when_token_present(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "gho_test")
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.setattr("src.api.routers.settings.shutil.which", lambda cmd: "/usr/bin/" + cmd)

    servers, summary = collect_mcp_status(_cfg(mcp_google_maps_enabled=False, mcp_slack_enabled=False))
    by_name = {s["name"]: s for s in servers}
    assert by_name["github"]["ready"] is True
    assert by_name["github"]["hint"] == ""
    assert summary["ready_total"] == summary["enabled_total"]
