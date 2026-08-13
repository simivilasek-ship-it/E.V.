"""
E.V. Skill — MCP Time
Timezone-aware dotazy na čas přes MCP Time server.

Příkazy:
  „kolik je hodin v Tokiu"         → čas v Asii/Tokio
  „jaký je čas v New Yorku"        → čas v America/New_York
  „časové pásmo Londýn"            → info o časovém pásmu
  „kolik je hodin"                 → lokální čas (Europe/Prague)
"""

import re
import logging

logger = logging.getLogger(__name__)

_bridge = None

# Mapování měst/zemí na IANA timezone
_CITY_TZ = {
    # Evropa
    "londyn": "Europe/London",
    "london": "Europe/London",
    "pariz": "Europe/Paris",
    "paris": "Europe/Paris",
    "berlin": "Europe/Berlin",
    "vídeň": "Europe/Vienna",
    "viden": "Europe/Vienna",
    "vienna": "Europe/Vienna",
    "moskva": "Europe/Moscow",
    "moscow": "Europe/Moscow",
    "istanbul": "Europe/Istanbul",
    "amsterdam": "Europe/Amsterdam",
    "madrid": "Europe/Madrid",
    "rim": "Europe/Rome",
    "rome": "Europe/Rome",
    "varšava": "Europe/Warsaw",
    "varsava": "Europe/Warsaw",
    "budapest": "Europe/Budapest",
    "bratislava": "Europe/Bratislava",
    "Praha": "Europe/Prague",
    "praha": "Europe/Prague",
    # Amerika
    "new york": "America/New_York",
    "new_york": "America/New_York",
    "los angeles": "America/Los_Angeles",
    "chicago": "America/Chicago",
    "toronto": "America/Toronto",
    "sao paulo": "America/Sao_Paulo",
    "mexico city": "America/Mexico_City",
    # Asie
    "tokio": "Asia/Tokyo",
    "tokyo": "Asia/Tokyo",
    "peking": "Asia/Shanghai",
    "beijing": "Asia/Shanghai",
    "shanghai": "Asia/Shanghai",
    "seoul": "Asia/Seoul",
    "seoul": "Asia/Seoul",
    "bombaj": "Asia/Kolkata",
    "mumbai": "Asia/Kolkata",
    "delhi": "Asia/Kolkata",
    "dubai": "Asia/Dubai",
    "bangkok": "Asia/Bangkok",
    "singapur": "Asia/Singapore",
    "singapore": "Asia/Singapore",
    "jakarta": "Asia/Jakarta",
    # Austrálie / Pacifik
    "sydney": "Australia/Sydney",
    "melbourne": "Australia/Melbourne",
    "auckland": "Pacific/Auckland",
}


def _get_bridge():
    global _bridge
    if _bridge is None:
        try:
            from mcp_bridge import get_mcp_bridge
            _bridge = get_mcp_bridge()
        except Exception as e:
            logger.warning(f"MCP time bridge nedostupný: {e}")
    return _bridge


def _available() -> bool:
    b = _get_bridge()
    return b is not None and b.is_available("time")


def _call(tool: str, args: dict) -> str:
    result = _get_bridge().call_tool("time", tool, args)
    if not result:
        return "(prázdný výsledek)"
    if len(result) > 1000:
        result = result[:1000] + "\n…(zkráceno)"
    return result


def _find_timezone(text: str) -> str:
    """Najde IANA timezone z textu, nebo vrátí lokální Prague."""
    lower = text.lower()
    for city, tz in _CITY_TZ.items():
        if city in lower:
            return tz
    # Zkus přímo IANA formát (např. "Europe/Tokyo")
    m = re.search(r"\b([A-Z][a-z]+/[A-Z][a-zA-Z_]+)\b", text)
    if m:
        return m.group(1)
    return "Europe/Prague"


# ── Patterny ──────────────────────────────────────────

_TIME_RE = re.compile(
    r"\b(kolik\s+je\s+hodin|jaky\s+je\s+cas|jaký\s+je\s+čas|co\s+je\s+za\s+cas|co\s+je\s+za\s+čas|current\s+time|what\s+time)\b",
    re.IGNORECASE,
)
_TZ_INFO_RE = re.compile(
    r"\b(casove\s+pasmo|časové\s+pásmo|timezone|time\s+zone|convert\s+time|preved\s+cas|převeď\s+čas)\b",
    re.IGNORECASE,
)
_CONVERT_RE = re.compile(
    r"\b(\d{1,2}:\d{2})\s+(?:z\s+|from\s+)?(.+?)\s+(?:v\s+|na\s+|to\s+)(.+)",
    re.IGNORECASE,
)


def _handle_time(text: str):
    m = _TIME_RE.search(text)
    if not m:
        return None, None
    if not _available():
        return None, None  # fallback na lokální get_time v LocalRouter
    tz = _find_timezone(text)
    result = _call("get_current_time", {"timezone": tz})
    label = tz.split("/")[-1].replace("_", " ")
    return f"**Aktuální čas** ({label}):\n{result}", {"action": "answer", "params": {}}


def _handle_tz_info(text: str):
    m = _TZ_INFO_RE.search(text)
    if not m:
        return None, None
    if not _available():
        return "MCP Time není dostupný.", {"action": "answer", "params": {}}
    tz = _find_timezone(text)
    result = _call("get_current_time", {"timezone": tz})
    label = tz.split("/")[-1].replace("_", " ")
    return f"**Časové pásmo** {label} (`{tz}`):\n{result}", {"action": "answer", "params": {}}


def _handle_convert(text: str):
    m = _CONVERT_RE.search(text)
    if not m:
        return None, None
    if not _available():
        return "MCP Time není dostupný.", {"action": "answer", "params": {}}
    time_str = m.group(1)
    from_loc = m.group(2).strip()
    to_loc = m.group(3).strip()
    from_tz = _find_timezone(from_loc)
    to_tz = _find_timezone(to_loc)
    result = _call("convert_time", {
        "source_timezone": from_tz,
        "time": time_str,
        "target_timezone": to_tz,
    })
    return f"**Převod času** {time_str} ({from_tz} → {to_tz}):\n{result}", {"action": "answer", "params": {}}


def get_routes():
    return [
        {"pattern": _CONVERT_RE, "handler": _handle_convert},
        {"pattern": _TIME_RE,    "handler": _handle_time},
        {"pattern": _TZ_INFO_RE, "handler": _handle_tz_info},
    ]


def get_actions():
    return {}
