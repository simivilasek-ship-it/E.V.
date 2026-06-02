"""
tests/test_sandbox.py — testy pro SandboxedPluginRunner a MCP opt-in servery.
"""
import os
import sys
import pytest

# Přidej kořen projektu do sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugin_system import SandboxedPluginRunner


# ── Sandbox testy ─────────────────────────────────────

def test_should_isolate_dangerous():
    """Plugin s system.exec musí být izolován."""
    runner = SandboxedPluginRunner()
    assert runner.should_isolate(["system.exec"]) is True


def test_should_isolate_safe():
    """Plugin s pouhou 'answer' permissions nesmí být izolován."""
    runner = SandboxedPluginRunner()
    assert runner.should_isolate(["answer"]) is False


# ── MCP opt-in testy ─────────────────────────────────

def test_mcp_discord_disabled_without_token(monkeypatch):
    """Bez DISCORD_TOKEN nesmí být Discord MCP registrován."""
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    from mcp_bridge import create_mcp_bridge
    bridge = create_mcp_bridge({})
    assert "discord" not in bridge.get_server_names()


def test_mcp_notion_disabled_without_token(monkeypatch):
    """Bez NOTION_API_KEY nesmí být Notion MCP registrován."""
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    from mcp_bridge import create_mcp_bridge
    bridge = create_mcp_bridge({})
    assert "notion" not in bridge.get_server_names()
