"""
E.V. Skill — MCP Sequential Thinking
Krok-za-krokem přemýšlení pro složité úkoly přes MCP server.

Příkazy:
  „přemýšlej jak napsat funkci"       → krok-za-krokem analýza
  „rozlož na kroky jak zoptimalizovat kód" → breakdown na kroky
  „krok za krokem jak nasadit server" → sekvenční analýza
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
            logger.warning(f"MCP sequential-thinking bridge nedostupný: {e}")
    return _bridge


def _available() -> bool:
    b = _get_bridge()
    return b is not None and b.is_available("sequential-thinking")


def _call_thinking(task: str, total_thoughts: int = 5) -> str:
    bridge = _get_bridge()
    if not bridge:
        return "MCP Sequential Thinking není dostupný."
    result = bridge.call_tool(
        "sequential-thinking",
        "sequentialthinking",
        {
            "thought": task,
            "nextThoughtNeeded": True,
            "thoughtNumber": 1,
            "totalThoughts": total_thoughts,
        },
    )
    if not result:
        return "(prázdný výsledek)"
    if len(result) > 3000:
        result = result[:3000] + "\n…(zkráceno)"
    return result


# ── Patterny ──────────────────────────────────────────

_THINK_RE = re.compile(
    r"\b(premysli|přemýšlej|rozmysli|rozmyslet)\s+(jak|co|proc|proč|zda|o\s+)?\s*(.+)",
    re.IGNORECASE,
)
_STEPS_RE = re.compile(
    r"\b(rozloz\s+na\s+kroky|rozlož\s+na\s+kroky|step\s+by\s+step|krok\s+za\s+krokem|analyze\s+step\s+by\s+step)\s*(.+)?",
    re.IGNORECASE,
)
_ANALYZE_RE = re.compile(
    r"\b(analyzuj|analyze|porad\s+jak|poraď\s+jak)\s+(.+)",
    re.IGNORECASE,
)


def _handle_think(text: str):
    m = _THINK_RE.search(text)
    if not m:
        return None, None
    if not _available():
        return "MCP Sequential Thinking není dostupný.", {"action": "answer", "params": {}}
    task = (m.group(3) or "").strip()
    if not task:
        return "Nerozuměl jsem, o čem mám přemýšlet.", {"action": "answer", "params": {}}
    result = _call_thinking(task)
    return f"**Krok-za-krokem přemýšlení:** {task}\n\n{result}", {"action": "answer", "params": {}}


def _handle_steps(text: str):
    m = _STEPS_RE.search(text)
    if not m:
        return None, None
    if not _available():
        return "MCP Sequential Thinking není dostupný.", {"action": "answer", "params": {}}
    task = (m.group(2) or "").strip() or text
    result = _call_thinking(f"Rozlož na konkrétní kroky: {task}", total_thoughts=7)
    return f"**Rozklad na kroky:** {task}\n\n{result}", {"action": "answer", "params": {}}


def _handle_analyze(text: str):
    m = _ANALYZE_RE.search(text)
    if not m:
        return None, None
    if not _available():
        return "MCP Sequential Thinking není dostupný.", {"action": "answer", "params": {}}
    task = (m.group(2) or "").strip()
    if not task:
        return None, None
    result = _call_thinking(task)
    return f"**Analýza:** {task}\n\n{result}", {"action": "answer", "params": {}}


def get_routes():
    return [
        {"pattern": _STEPS_RE,   "handler": _handle_steps},
        {"pattern": _THINK_RE,   "handler": _handle_think},
        {"pattern": _ANALYZE_RE, "handler": _handle_analyze},
    ]


def get_actions():
    return {}
