"""
E.V. Skill — MCP Memory (Knowledge Graph)
Persistentní paměť jako knowledge graph přes @modelcontextprotocol/server-memory.
Ukládá entity a jejich vztahy — silnější než prostý text.

Příkazy:
  „zapamatuj si: Petr má rád kávu"     → vytvoří entitu Petr s vlastností
  „co víš o Petrovi?"                   → recall z knowledge graphu
  „přidej do paměti: projekt Jarvis je v ~/Stažené"
  „zapomeň Petra"                       → smaže entitu
"""

import re
import logging

logger = logging.getLogger(__name__)

_bridge = None


def _get_bridge():
    global _bridge
    if _bridge is None:
        try:
            from mcp_bridge import get_mcp_bridge
            _bridge = get_mcp_bridge()
        except Exception as e:
            logger.warning(f"MCP memory bridge nedostupný: {e}")
    return _bridge


def _available() -> bool:
    b = _get_bridge()
    return b is not None and b.is_available("mcp-memory")


def _call(tool: str, args: dict) -> str:
    result = _get_bridge().call_tool("mcp-memory", tool, args)
    return result or "(prázdný výsledek)"


# ── Patterny ──────────────────────────────────────────

_STORE_RE = re.compile(
    r"\b(zapamatuj\s+si|pamatuj|pridej\s+do\s+pameti|remember|uloz\s+si)\b[:\s]+(.{3,200})",
    re.IGNORECASE,
)
_RECALL_RE = re.compile(
    r"\b(co\s+vis\s+o|co\s+si\s+pamatujes\s+o|recall|vzpomen\s+si\s+na|hledej\s+v\s+pameti)\b\s+(.+)",
    re.IGNORECASE,
)
_FORGET_RE = re.compile(
    r"\b(zapomen|zapomenout|smaz\s+z\s+pameti|delete\s+from\s+memory)\b\s+(.+)",
    re.IGNORECASE,
)
_GRAPH_RE = re.compile(
    r"\b(ukazgraph|zobraz\s+pamet|knowledge\s+graph|co\s+vis)\b$",
    re.IGNORECASE,
)


def _handle_store(text: str):
    m = _STORE_RE.search(text)
    if not m:
        return None, None
    content = m.group(2).strip()

    if not _available():
        # Fallback na základní JarvisMemory
        try:
            from memory import JarvisMemory
            from config import CONFIG
            mem = JarvisMemory(CONFIG)
            mem.store(content, importance=0.8, tags=["manual"])
            return f"Uloženo do paměti: {content[:60]}", {"action": "answer", "params": {}}
        except Exception:
            return "Paměť není dostupná.", {"action": "answer", "params": {}}

    # Vytvoř entitu v knowledge graphu
    result = _call("create_entities", {
        "entities": [{
            "name": content[:50],
            "entityType": "fact",
            "observations": [content],
        }]
    })
    return f"Zapamatováno v knowledge graphu: {content[:60]}", {"action": "answer", "params": {}}


def _handle_recall(text: str):
    m = _RECALL_RE.search(text)
    if not m:
        return None, None
    query = m.group(2).strip()

    if not _available():
        # Fallback na základní JarvisMemory
        try:
            from memory import JarvisMemory
            from config import CONFIG
            mem = JarvisMemory(CONFIG)
            results = mem.recall(query, top_k=5)
            if not results:
                return f"Nic o '{query}' v paměti.", {"action": "answer", "params": {}}
            lines = [r["content"][:100] for r in results[:3]]
            return f"Z paměti o '{query}':\n" + "\n".join(f"• {l}" for l in lines), \
                   {"action": "answer", "params": {}}
        except Exception:
            return "Paměť není dostupná.", {"action": "answer", "params": {}}

    result = _call("search_nodes", {"query": query})
    if not result or result == "(prázdný výsledek)":
        return f"Nic o '{query}' v knowledge graphu.", {"action": "answer", "params": {}}
    return f"**Knowledge graph — {query}**:\n{result[:2000]}", {"action": "answer", "params": {}}


def _handle_forget(text: str):
    m = _FORGET_RE.search(text)
    if not m:
        return None, None
    entity = m.group(2).strip()

    if not _available():
        return "MCP Memory není dostupný.", {"action": "answer", "params": {}}

    result = _call("delete_entities", {"entityNames": [entity]})
    return f"Zapomenuto: {entity}", {"action": "answer", "params": {}}


def _handle_graph(text: str):
    if not _available():
        return None, None
    result = _call("read_graph", {})
    if not result or result == "(prázdný výsledek)":
        return "Knowledge graph je prázdný.", {"action": "answer", "params": {}}
    return f"**Knowledge graph**:\n{result[:3000]}", {"action": "answer", "params": {}}


def get_routes():
    return [
        {"pattern": _FORGET_RE, "handler": _handle_forget},
        {"pattern": _GRAPH_RE,  "handler": _handle_graph},
        {"pattern": _STORE_RE,  "handler": _handle_store},
        {"pattern": _RECALL_RE, "handler": _handle_recall},
    ]


def get_actions():
    return {}
