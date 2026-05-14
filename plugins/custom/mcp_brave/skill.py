"""
JARVIS Skill — MCP Brave Search
Vyhledávání přes Brave Search API skrze MCP server.
Vrací skutečné výsledky přímo do chatu — ne jen otevření prohlížeče.

Vyžaduje: BRAVE_API_KEY v .env nebo config.json
Získej klíč: https://api.search.brave.com/
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
            logger.warning(f"MCP brave bridge nedostupný: {e}")
    return _bridge


def _available() -> bool:
    b = _get_bridge()
    return b is not None and b.is_available("brave-search")


# ── Patterny ──────────────────────────────────────────

_WEB_RE = re.compile(
    r"\b(vyhledej|najdi\s+na\s+internetu|brave\s+search|web\s+search)\b\s+(.+)",
    re.IGNORECASE,
)
_NEWS_RE = re.compile(
    r"\b(novinky|zpravy|news)\b\s+(?:o\s+|about\s+)?(.+)",
    re.IGNORECASE,
)
_WHO_RE = re.compile(
    r"\b(kdo\s+je|co\s+je|what\s+is|who\s+is)\b\s+(.+)",
    re.IGNORECASE,
)
_VIDEO_RE = re.compile(
    r"\b(brave\s+video|najdi\s+video)\b\s+(.+)",
    re.IGNORECASE,
)


def _format_results(raw: str, max_chars: int = 2500) -> str:
    """Zkrátí výsledky na rozumnou délku pro chat."""
    if not raw or raw == "(prázdný výsledek)":
        return "Žádné výsledky."
    if len(raw) > max_chars:
        raw = raw[:max_chars] + "\n…(zkráceno)"
    return raw


def _handle_web_search(text: str):
    m = _WEB_RE.search(text)
    if not m:
        return None, None
    query = m.group(2).strip()
    if not _available():
        return (
            "Brave Search MCP není dostupný. "
            "Nastav BRAVE_API_KEY v .env (https://api.search.brave.com/).",
            {"action": "answer", "params": {}},
        )
    result = _get_bridge().call_tool("brave-search", "brave_web_search", {
        "query": query, "count": 5,
    })
    return f"**Brave Search: {query}**\n\n{_format_results(result)}", \
           {"action": "answer", "params": {}}


def _handle_news(text: str):
    m = _NEWS_RE.search(text)
    if not m:
        return None, None
    query = m.group(2).strip()
    if not _available():
        return ("Brave Search MCP není dostupný.", {"action": "answer", "params": {}})
    result = _get_bridge().call_tool("brave-search", "brave_news_search", {
        "query": query, "count": 5,
    })
    return f"**Novinky: {query}**\n\n{_format_results(result)}", \
           {"action": "answer", "params": {}}


def _handle_who_what(text: str):
    m = _WHO_RE.search(text)
    if not m:
        return None, None
    query = m.group(2).strip()
    if not _available():
        return None, None  # Fallback na LLM/Wikipedia
    result = _get_bridge().call_tool("brave-search", "brave_web_search", {
        "query": query, "count": 3,
    })
    if not result or result == "(prázdný výsledek)" or "Chyba" in result:
        return None, None  # Nech LLM odpovědět
    return f"**{query}** (Brave Search):\n\n{_format_results(result, 1500)}", \
           {"action": "answer", "params": {}}


def _handle_video_search(text: str):
    m = _VIDEO_RE.search(text)
    if not m:
        return None, None
    query = m.group(2).strip()
    if not _available():
        return ("Brave Search MCP není dostupný.", {"action": "answer", "params": {}})
    result = _get_bridge().call_tool("brave-search", "brave_video_search", {
        "query": query, "count": 3,
    })
    return f"**Videa: {query}**\n\n{_format_results(result)}", \
           {"action": "answer", "params": {}}


# ── Skill API ─────────────────────────────────────────

def get_routes():
    return [
        {"pattern": _NEWS_RE,  "handler": _handle_news},
        {"pattern": _VIDEO_RE, "handler": _handle_video_search},
        {"pattern": _WEB_RE,   "handler": _handle_web_search},
        {"pattern": _WHO_RE,   "handler": _handle_who_what},
    ]


def get_actions():
    return {}
