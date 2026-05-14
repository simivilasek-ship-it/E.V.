"""
JARVIS — MCP Bridge
Správce připojení k MCP serverům (filesystem, brave-search, …).
Každý server se spouští jako subprocess přes stdio.
Volání jsou synchronní (asyncio.run) pro kompatibilitu s ostatními moduly.
"""

from __future__ import annotations
import asyncio
import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    logger.warning("mcp balíček není nainstalován: pip install mcp")


# ── Datové struktury ──────────────────────────────────

@dataclass
class MCPTool:
    name:        str
    description: str
    server:      str
    input_schema: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.server}/{self.name}: {self.description[:60]}"


@dataclass
class MCPServerConfig:
    name:    str          # logické jméno (filesystem, brave-search)
    command: str          # npx / node / python
    args:    List[str]    # argumenty
    env:     Dict[str, str] = field(default_factory=dict)  # extra env vars
    enabled: bool = True


# ── MCP Bridge ────────────────────────────────────────

class MCPBridge:
    """
    Správce MCP serverů pro JARVIS.
    call_tool() je synchronní — spouští asyncio smyčku v samostatném vlákně,
    aby nerozbil GUI vlákno.
    """

    def __init__(self):
        self._servers: Dict[str, MCPServerConfig] = {}
        self._tools:   Dict[str, MCPTool] = {}   # key = "server/tool"
        self._lock = threading.Lock()

    # ── Registrace serverů ────────────────────────────

    def register(self, config: MCPServerConfig) -> None:
        if not config.enabled:
            logger.debug(f"MCP server '{config.name}' je zakázán")
            return
        self._servers[config.name] = config
        logger.info(f"MCP server registrován: {config.name} ({config.command} {' '.join(config.args[:2])}…)")

    # ── Inicializace — zjistí dostupné nástroje ───────

    def discover_tools(self, server_name: str) -> List[MCPTool]:
        """Připojí se k serveru, stáhne seznam nástrojů a odpojí se."""
        if not HAS_MCP:
            return []
        cfg = self._servers.get(server_name)
        if not cfg:
            return []

        async def _fetch():
            env = os.environ.copy()
            env.update(cfg.env)
            params = StdioServerParameters(
                command=cfg.command, args=cfg.args, env=env)
            try:
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        resp = await session.list_tools()
                        tools = []
                        for t in resp.tools:
                            mt = MCPTool(
                                name=t.name,
                                description=t.description or "",
                                server=server_name,
                                input_schema=t.inputSchema or {},
                            )
                            tools.append(mt)
                        return tools
            except Exception as e:
                logger.error(f"MCP discover '{server_name}': {e}")
                return []

        tools = self._run(server_name, _fetch())
        with self._lock:
            for t in tools:
                self._tools[f"{server_name}/{t.name}"] = t
        logger.info(f"MCP '{server_name}': {len(tools)} nástrojů nalezeno")
        return tools

    def discover_all(self) -> Dict[str, List[MCPTool]]:
        result = {}
        for name in list(self._servers):
            result[name] = self.discover_tools(name)
        return result

    # ── Volání nástrojů ───────────────────────────────

    def call_tool(self, server_name: str, tool_name: str,
                  arguments: Dict[str, Any]) -> str:
        """
        Synchronně zavolá MCP nástroj a vrátí textový výsledek.
        Při chybě vrátí chybovou zprávu (nikdy nevyvolá výjimku).
        """
        if not HAS_MCP:
            return "MCP není nainstalován (pip install mcp)"
        cfg = self._servers.get(server_name)
        if not cfg:
            return f"MCP server '{server_name}' není registrován"

        async def _call():
            env = os.environ.copy()
            env.update(cfg.env)
            params = StdioServerParameters(
                command=cfg.command, args=cfg.args, env=env)
            try:
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(tool_name, arguments)
                        # Extrahuj text z výsledku
                        parts = []
                        for item in (result.content or []):
                            if hasattr(item, "text") and item.text:
                                parts.append(item.text)
                            elif hasattr(item, "data"):
                                parts.append(str(item.data))
                        return "\n".join(parts) if parts else "(prázdný výsledek)"
            except Exception as e:
                logger.error(f"MCP call '{server_name}/{tool_name}': {e}")
                return f"Chyba MCP: {e}"

        return self._run(server_name, _call())

    # ── Pomocné ───────────────────────────────────────

    def _run(self, server_name: str, coro) -> Any:
        """Spustí korutinu synchronně v izolované smyčce."""
        try:
            return asyncio.run(coro)
        except Exception as e:
            logger.error(f"MCP asyncio chyba ({server_name}): {e}")
            return None

    def list_tools(self) -> List[MCPTool]:
        with self._lock:
            return list(self._tools.values())

    def is_available(self, server_name: str) -> bool:
        return server_name in self._servers and HAS_MCP

    def get_server_names(self) -> List[str]:
        return list(self._servers.keys())


# ── Továrna — výchozí konfigurace pro JARVIS ─────────

def create_mcp_bridge(config: Dict[str, Any]) -> MCPBridge:
    """
    Vytvoří MCPBridge s výchozími servery.
    Brave Search vyžaduje BRAVE_API_KEY v .env nebo config.
    """
    bridge = MCPBridge()

    # ── Filesystem MCP ────────────────────────────────
    home = os.path.expanduser("~")
    allowed_dirs = config.get("mcp_filesystem_dirs", [
        home,
        os.path.join(home, "Dokumenty"),
        os.path.join(home, "Plocha"),
        os.path.join(home, "Desktop"),
        os.path.join(home, "Downloads"),
        os.path.join(home, "Stažené"),
    ])
    # Filtruj neexistující složky
    existing = [d for d in allowed_dirs if os.path.isdir(d)]
    if not existing:
        existing = [home]

    bridge.register(MCPServerConfig(
        name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem"] + existing,
        enabled=config.get("mcp_filesystem_enabled", True),
    ))

    # ── Brave Search MCP ─────────────────────────────
    brave_key = (
        config.get("brave_api_key")
        or os.environ.get("BRAVE_API_KEY")
        or ""
    )
    bridge.register(MCPServerConfig(
        name="brave-search",
        command="npx",
        args=["-y", "@brave/brave-search-mcp-server", "--transport", "stdio"],
        env={"BRAVE_API_KEY": brave_key} if brave_key else {},
        enabled=bool(brave_key) and config.get("mcp_brave_enabled", True),
    ))

    if not brave_key:
        logger.info("Brave Search MCP: BRAVE_API_KEY není nastavena → zakázáno")

    return bridge


# ── Singleton ─────────────────────────────────────────

_bridge: Optional[MCPBridge] = None


def get_mcp_bridge(config: Optional[Dict[str, Any]] = None) -> MCPBridge:
    global _bridge
    if _bridge is None:
        _bridge = create_mcp_bridge(config or {})
    return _bridge
