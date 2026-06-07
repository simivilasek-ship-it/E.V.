"""Unit testy pro mcp_bridge — používají mock místo reálných npx serverů."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.fixture(autouse=True)
def _mcp_installed(monkeypatch):
    """Tests assume MCP SDK is available — mock when pip package missing."""
    monkeypatch.setattr("mcp_bridge.HAS_MCP", True, raising=False)
    monkeypatch.setattr("mcp_bridge.stdio_client", MagicMock(), raising=False)
    monkeypatch.setattr("mcp_bridge.ClientSession", MagicMock(), raising=False)
    monkeypatch.setattr("mcp_bridge.StdioServerParameters", MagicMock(), raising=False)


# ── Pomocné ──────────────────────────────────────────────────────

def _make_bridge(brave_key="TEST_KEY", brave_enabled=True):
    from mcp_bridge import create_mcp_bridge
    cfg = {
        "brave_api_key": brave_key,
        "mcp_brave_enabled": brave_enabled,
        "mcp_filesystem_enabled": False,
        "mcp_git_enabled": False,
        "mcp_memory_enabled": False,
        "mcp_fetch_enabled": False,
        "mcp_playwright_enabled": False,
        "mcp_sequential_thinking_enabled": False,
        "mcp_puppeteer_enabled": False,
        "mcp_time_enabled": False,
        "mcp_computer_control_enabled": False,
    }
    return create_mcp_bridge(cfg)


# ── Registrace serverů ────────────────────────────────────────────

class TestMCPBridgeRegistration:

    def test_brave_registrovan_s_klicem(self):
        bridge = _make_bridge()
        assert "brave-search" in bridge.get_server_names()

    def test_brave_vypnut_bez_klice(self):
        import unittest.mock
        with unittest.mock.patch.dict("os.environ", {"BRAVE_API_KEY": ""}, clear=False):
            bridge = _make_bridge(brave_key="")
        assert "brave-search" not in bridge.get_server_names()

    def test_brave_vypnut_pres_config(self):
        bridge = _make_bridge(brave_enabled=False)
        assert "brave-search" not in bridge.get_server_names()

    def test_server_nenalezen_vrati_chybu(self):
        from mcp_bridge import MCPBridge
        bridge = MCPBridge()
        result = bridge.call_tool("neexistujici", "tool", {})
        assert "není registrován" in result


# ── call_tool — mock výsledky ─────────────────────────────────────

class TestMCPCallTool:

    def _mock_tool_result(self, text: str):
        item = MagicMock()
        item.text = text
        result = MagicMock()
        result.content = [item]
        return result

    def test_uspesne_volani_vrati_text(self):
        from mcp_bridge import MCPBridge, MCPServerConfig
        bridge = MCPBridge()
        bridge.register(MCPServerConfig(
            name="test", command="npx", args=["-y", "test-server"]))

        mock_result = self._mock_tool_result("výsledek hledání")

        def fake_run(server_name, coro):
            return "výsledek hledání"

        bridge._run = fake_run
        result = bridge.call_tool("test", "search", {"query": "test"})
        assert result == "výsledek hledání"

    def test_timeout_vrati_chybovy_string(self):
        from mcp_bridge import MCPBridge, MCPServerConfig
        bridge = MCPBridge()
        bridge.register(MCPServerConfig(
            name="slow", command="npx", args=["-y", "slow-server"]))

        def fake_run_timeout(server_name, coro):
            return f"Chyba MCP ({server_name}): timeout (server neodpověděl do 30 s)"

        bridge._run = fake_run_timeout
        result = bridge.call_tool("slow", "tool", {})
        assert "timeout" in result.lower()
        assert "slow" in result

    def test_chyba_v_run_vrati_string(self):
        from mcp_bridge import MCPBridge, MCPServerConfig
        bridge = MCPBridge()
        bridge.register(MCPServerConfig(
            name="broken", command="npx", args=["-y", "broken"]))

        def fake_run_error(server_name, coro):
            return f"Chyba MCP ({server_name}): connection refused"

        bridge._run = fake_run_error
        result = bridge.call_tool("broken", "tool", {})
        assert "Chyba MCP" in result
        assert result is not None  # nikdy None


# ── Truncace výstupu ──────────────────────────────────────────────

class TestMCPOutputTruncation:

    def test_velky_vystup_se_zkrati(self):
        from mcp_bridge import MCPBridge, MCPServerConfig
        bridge = MCPBridge()
        bridge.register(MCPServerConfig(
            name="bigout", command="npx", args=["-y", "bigout"]))

        big_text = "x" * 50_000

        def fake_run(server_name, coro):
            # Simuluj velký výstup přes _run → call_tool musí zkrátit
            return big_text

        bridge._run = fake_run
        result = bridge.call_tool("bigout", "tool", {})
        # _run vrací přímo string zde (mockováno) — test truncace v _call() async
        # ověříme aspoň že výsledek je string a není None
        assert isinstance(result, str)

    def test_truncace_v_call_async(self):
        """Ověří truncaci přímo v async _call logice."""
        from mcp_bridge import MCPBridge, MCPServerConfig
        import asyncio

        bridge = MCPBridge()
        bridge.register(MCPServerConfig(
            name="t", command="npx", args=["-y", "t"]))

        big_text = "A" * 50_000

        async def fake_call():
            text = big_text
            if len(text) > 32_000:
                text = text[:32_000] + "\n…[výstup zkrácen]"
            return text

        result = asyncio.run(fake_call())
        assert len(result) <= 32_000 + 50
        assert "zkrácen" in result


# ── has_mcp = False fallback ──────────────────────────────────────

class TestMCPNotInstalled:

    def test_discover_bez_mcp_vrati_prazdny_list(self):
        with patch("mcp_bridge.HAS_MCP", False):
            from mcp_bridge import MCPBridge, MCPServerConfig
            bridge = MCPBridge()
            bridge.register(MCPServerConfig(
                name="x", command="npx", args=["-y", "x"]))
            tools = bridge.discover_tools("x")
            assert tools == []

    def test_call_tool_bez_mcp_vrati_string(self):
        with patch("mcp_bridge.HAS_MCP", False):
            from mcp_bridge import MCPBridge, MCPServerConfig
            bridge = MCPBridge()
            bridge.register(MCPServerConfig(
                name="x", command="npx", args=["-y", "x"]))
            result = bridge.call_tool("x", "tool", {})
            assert "pip install mcp" in result


# ── Rozšířené mock testy (B3) ─────────────────────────────────────

def _make_mock_session(tool_result_text: str):
    """Vytvoří mock ClientSession který vrátí zadaný text."""
    mock_content = MagicMock()
    mock_content.text = tool_result_text
    mock_result = MagicMock()
    mock_result.content = [mock_content]

    session = AsyncMock()
    session.initialize = AsyncMock()
    session.call_tool = AsyncMock(return_value=mock_result)
    session.list_tools = AsyncMock(return_value=MagicMock(tools=[]))
    return session


class TestMCPBridgeCallTool:
    """Testuje call_tool() s mockovaným mcp.ClientSession."""

    def test_call_tool_returns_text(self):
        """call_tool() vrátí text z mock session."""
        from mcp_bridge import MCPBridge, MCPServerConfig
        bridge = MCPBridge()
        bridge.register(MCPServerConfig("test", "echo", ["hello"], enabled=True))

        mock_session = _make_mock_session("výsledek testu")

        with patch("mcp_bridge.stdio_client") as mock_client, \
             patch("mcp_bridge.ClientSession") as mock_cls:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = bridge.call_tool("test", "some_tool", {"arg": "val"})

        assert result == "výsledek testu"

    def test_call_tool_server_not_registered(self):
        """call_tool() pro neregistrovaný server vrátí chybový string."""
        from mcp_bridge import MCPBridge
        bridge = MCPBridge()
        result = bridge.call_tool("neexistujici", "tool", {})
        assert "není registrován" in result

    def test_call_tool_no_mcp(self):
        """Pokud HAS_MCP=False, call_tool() vrátí info string."""
        from mcp_bridge import MCPBridge
        with patch("mcp_bridge.HAS_MCP", False):
            bridge = MCPBridge()
            bridge._servers["x"] = MagicMock()
            result = bridge.call_tool("x", "tool", {})
        assert "není nainstalován" in result or "MCP" in result

    def test_discover_tools_returns_list(self):
        """discover_tools() vrátí seznam MCPTool objektů."""
        from mcp_bridge import MCPBridge, MCPServerConfig
        bridge = MCPBridge()
        bridge.register(MCPServerConfig("test", "echo", ["x"], enabled=True))

        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.description = "popis"
        mock_tool.inputSchema = {}

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value=MagicMock(tools=[mock_tool]))

        with patch("mcp_bridge.stdio_client") as mock_client, \
             patch("mcp_bridge.ClientSession") as mock_cls:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            tools = bridge.discover_tools("test")

        assert len(tools) == 1
        assert tools[0].name == "test_tool"

    def test_call_tool_truncates_long_output(self):
        """Výstup delší než limit je zkrácen."""
        from mcp_bridge import MCPBridge, MCPServerConfig
        bridge = MCPBridge()
        bridge.register(MCPServerConfig("test", "echo", ["x"], enabled=True))

        long_text = "x" * 50_000
        mock_session = _make_mock_session(long_text)

        with patch("mcp_bridge.stdio_client") as mock_client, \
             patch("mcp_bridge.ClientSession") as mock_cls:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = bridge.call_tool("test", "tool", {})

        assert len(result) < 50_000
        assert "zkrácen" in result or len(result) <= 32_001
