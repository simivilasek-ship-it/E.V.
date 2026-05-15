"""
JARVIS Skill — MCP Puppeteer
Browser automation přes Puppeteer MCP server.

Příkazy:
  „screenshot webu google.com"         → screenshot stránky
  „otevři v prohlížeči https://..."    → navigace na URL
  „klikni na tlačítko Přihlásit"       → klik na element
  „vyplň formulář jméno = Jan"         → vyplnění pole
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
            logger.warning(f"MCP puppeteer bridge nedostupný: {e}")
    return _bridge


def _available() -> bool:
    b = _get_bridge()
    return b is not None and b.is_available("puppeteer")


def _call(tool: str, args: dict) -> str:
    result = _get_bridge().call_tool("puppeteer", tool, args)
    if not result:
        return "(prázdný výsledek)"
    if len(result) > 3000:
        result = result[:3000] + "\n…(zkráceno)"
    return result


def _extract_url(text: str) -> str:
    m = re.search(r"(https?://\S+|www\.\S+)", text, re.IGNORECASE)
    if m:
        url = m.group(1)
        if not url.startswith("http"):
            url = "https://" + url
        return url
    # Zkus doménu z textu (např. "google.com")
    m2 = re.search(r"(\b[\w.-]+\.(com|cz|org|net|io|sk|de|uk)\b)", text, re.IGNORECASE)
    if m2:
        return "https://" + m2.group(1)
    return ""


# ── Patterny ──────────────────────────────────────────

_SCREENSHOT_RE = re.compile(
    r"\b(screenshot|snimek\s+obrazovky|vyfot|zachyt)\s+(?:webu?\s+|stranky?\s+|stránky?\s+)?(.+)",
    re.IGNORECASE,
)
_NAVIGATE_RE = re.compile(
    r"\b(otevri|otevři|naviguj|jdi\s+na|přejdi\s+na|prejdi\s+na|zobraz)\s+(?:v\s+prohlizeci\s+|v\s+prohlížeči\s+|stranku\s+|stránku\s+)?(.+)",
    re.IGNORECASE,
)
_CLICK_RE = re.compile(
    r"\b(klikni|klik|click)\s+(?:na\s+)?(.+)",
    re.IGNORECASE,
)
_FILL_RE = re.compile(
    r"\b(vypln|vyplň|fill|zadej)\s+(?:formular\s+|formulář\s+|pole\s+)?(.+?)\s*[=:]\s*(.+)",
    re.IGNORECASE,
)


def _handle_screenshot(text: str):
    m = _SCREENSHOT_RE.search(text)
    if not m:
        return None, None
    if not _available():
        return "MCP Puppeteer není dostupný.", {"action": "answer", "params": {}}
    target = (m.group(2) or "").strip()
    url = _extract_url(target) or _extract_url(text)
    if not url:
        return f"Nerozuměl jsem URL pro screenshot: '{target}'", {"action": "answer", "params": {}}
    result = _call("puppeteer_screenshot", {"url": url})
    return f"**Screenshot** `{url}`:\n{result}", {"action": "answer", "params": {}}


def _handle_navigate(text: str):
    m = _NAVIGATE_RE.search(text)
    if not m:
        return None, None
    if not _available():
        return "MCP Puppeteer není dostupný.", {"action": "answer", "params": {}}
    target = (m.group(2) or "").strip()
    url = _extract_url(target) or _extract_url(text)
    if not url:
        return f"Nerozuměl jsem URL: '{target}'", {"action": "answer", "params": {}}
    result = _call("puppeteer_navigate", {"url": url})
    return f"**Navigace** na `{url}`:\n{result}", {"action": "answer", "params": {}}


def _handle_click(text: str):
    m = _CLICK_RE.search(text)
    if not m:
        return None, None
    if not _available():
        return "MCP Puppeteer není dostupný.", {"action": "answer", "params": {}}
    selector = (m.group(2) or "").strip()
    result = _call("puppeteer_click", {"selector": selector})
    return f"**Klik** na '{selector}':\n{result}", {"action": "answer", "params": {}}


def _handle_fill(text: str):
    m = _FILL_RE.search(text)
    if not m:
        return None, None
    if not _available():
        return "MCP Puppeteer není dostupný.", {"action": "answer", "params": {}}
    selector = (m.group(2) or "").strip()
    value = (m.group(3) or "").strip()
    result = _call("puppeteer_fill", {"selector": selector, "value": value})
    return f"**Vyplnění** '{selector}' = '{value}':\n{result}", {"action": "answer", "params": {}}


def get_routes():
    return [
        {"pattern": _SCREENSHOT_RE, "handler": _handle_screenshot},
        {"pattern": _FILL_RE,       "handler": _handle_fill},
        {"pattern": _CLICK_RE,      "handler": _handle_click},
        {"pattern": _NAVIGATE_RE,   "handler": _handle_navigate},
    ]


def get_actions():
    return {}
