"""
JARVIS Skill — MCP Filesystem
Pokročilé souborové operace přes @modelcontextprotocol/server-filesystem.

Oproti základním file příkazům navíc:
- Čte obsah souborů (text, kód)
- Stromová struktura adresáře
- Full-text hledání v souborech
- Bezpečné přepisování (edit_file s patch)
"""

import re
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_bridge = None


def _get_bridge():
    global _bridge
    if _bridge is None:
        try:
            from mcp_bridge import get_mcp_bridge
            _bridge = get_mcp_bridge()
        except Exception as e:
            logger.warning(f"MCP filesystem bridge nedostupný: {e}")
    return _bridge


# ── Patterny ──────────────────────────────────────────

_READ_RE = re.compile(
    r"\b(prect[ií]|cti|zobraz\s+obsah|read\s+file|obsah\s+souboru)\b.{0,40}?([~/\w.\-]+\.\w+)",
    re.IGNORECASE,
)
_TREE_RE = re.compile(
    r"\b(strom|tree|struktura\s+slozky|vypis\s+slozku)\b.{0,30}?([~/\w.\-]+)",
    re.IGNORECASE,
)
_SEARCH_RE = re.compile(
    r"\b(hledej\s+v\s+souborech|fulltext|grep)\b\s+[\"']?(.+?)[\"']?\s*(?:v\s+|in\s+)?([~/\w.\-]*)",
    re.IGNORECASE,
)
_FIND_RE = re.compile(
    r"\b(najdi\s+soubor|find\s+file)\b\s+[\"']?(\S+)[\"']?",
    re.IGNORECASE,
)
_INFO_RE = re.compile(
    r"\b(info\s+o\s+souboru|file\s+info|velikost\s+souboru)\b.{0,20}?([~/\w.\-]+)",
    re.IGNORECASE,
)


# ── Handlery ──────────────────────────────────────────

def _handle_read(text: str):
    m = _READ_RE.search(text)
    if not m:
        return None, None
    path = os.path.expanduser(m.group(2).strip())
    bridge = _get_bridge()
    if not bridge or not bridge.is_available("filesystem"):
        return f"MCP filesystem není dostupný.", {"action": "answer", "params": {}}
    result = bridge.call_tool("filesystem", "read_file", {"path": path})
    # Zkrať na 2000 znaků pro chat
    if len(result) > 2000:
        result = result[:2000] + f"\n… (zkráceno, soubor má {len(result)} znaků)"
    return f"**{path}**:\n```\n{result}\n```", {"action": "answer", "params": {}}


def _handle_tree(text: str):
    m = _TREE_RE.search(text)
    if not m:
        return None, None
    path = os.path.expanduser(m.group(2).strip() or "~")
    bridge = _get_bridge()
    if not bridge or not bridge.is_available("filesystem"):
        return "MCP filesystem není dostupný.", {"action": "answer", "params": {}}
    result = bridge.call_tool("filesystem", "directory_tree", {"path": path})
    if len(result) > 3000:
        result = result[:3000] + "\n… (zkráceno)"
    return f"Struktura `{path}`:\n```\n{result}\n```", {"action": "answer", "params": {}}


def _handle_search_in_files(text: str):
    m = _SEARCH_RE.search(text)
    if not m:
        return None, None
    pattern = m.group(2).strip()
    path = os.path.expanduser(m.group(3).strip() if m.group(3) else "~")
    bridge = _get_bridge()
    if not bridge or not bridge.is_available("filesystem"):
        return "MCP filesystem není dostupný.", {"action": "answer", "params": {}}
    result = bridge.call_tool("filesystem", "search_files", {
        "path": path,
        "pattern": pattern,
    })
    if not result or result == "(prázdný výsledek)":
        return f"Nic nenalezeno pro '{pattern}' v `{path}`.", {"action": "answer", "params": {}}
    return f"Výsledky hledání '{pattern}':\n{result}", {"action": "answer", "params": {}}


def _handle_find(text: str):
    m = _FIND_RE.search(text)
    if not m:
        return None, None
    name = m.group(2).strip()
    bridge = _get_bridge()
    if not bridge or not bridge.is_available("filesystem"):
        return "MCP filesystem není dostupný.", {"action": "answer", "params": {}}
    result = bridge.call_tool("filesystem", "search_files", {
        "path": os.path.expanduser("~"),
        "pattern": name,
    })
    if not result or result == "(prázdný výsledek)":
        return f"Soubor '{name}' nenalezen.", {"action": "answer", "params": {}}
    return f"Nalezeno '{name}':\n{result}", {"action": "answer", "params": {}}


def _handle_info(text: str):
    m = _INFO_RE.search(text)
    if not m:
        return None, None
    path = os.path.expanduser(m.group(2).strip())
    bridge = _get_bridge()
    if not bridge or not bridge.is_available("filesystem"):
        return "MCP filesystem není dostupný.", {"action": "answer", "params": {}}
    result = bridge.call_tool("filesystem", "get_file_info", {"path": path})
    return f"Info o `{path}`:\n{result}", {"action": "answer", "params": {}}


# ── MCP filesystem akce (pro CommandExecutor bypass) ──

def _mcp_create_dir(path: str) -> str:
    bridge = _get_bridge()
    if not bridge or not bridge.is_available("filesystem"):
        return "MCP filesystem nedostupný"
    return bridge.call_tool("filesystem", "create_directory", {"path": path})


def _mcp_write_file(path: str, content: str) -> str:
    bridge = _get_bridge()
    if not bridge or not bridge.is_available("filesystem"):
        return "MCP filesystem nedostupný"
    return bridge.call_tool("filesystem", "write_file", {"path": path, "content": content})


def _mcp_move_file(source: str, destination: str) -> str:
    bridge = _get_bridge()
    if not bridge or not bridge.is_available("filesystem"):
        return "MCP filesystem nedostupný"
    return bridge.call_tool("filesystem", "move_file", {
        "source": source, "destination": destination})


def _mcp_list_dir(path: str) -> str:
    bridge = _get_bridge()
    if not bridge or not bridge.is_available("filesystem"):
        return "MCP filesystem nedostupný"
    return bridge.call_tool("filesystem", "list_directory", {"path": path})


# ── Skill API ─────────────────────────────────────────

def get_routes():
    return [
        {"pattern": _READ_RE,       "handler": _handle_read},
        {"pattern": _TREE_RE,       "handler": _handle_tree},
        {"pattern": _SEARCH_RE,     "handler": _handle_search_in_files},
        {"pattern": _FIND_RE,       "handler": _handle_find},
        {"pattern": _INFO_RE,       "handler": _handle_info},
    ]


def get_actions():
    return {
        "mcp_create_dir":  _mcp_create_dir,
        "mcp_write_file":  _mcp_write_file,
        "mcp_move_file":   _mcp_move_file,
        "mcp_list_dir":    _mcp_list_dir,
    }
