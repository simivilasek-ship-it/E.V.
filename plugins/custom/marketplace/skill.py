"""
E.V. Skill — Plugin Marketplace
Instalace, seznam a správa pluginů z GitHubu.

Příkazy:
  „marketplace seznam"                          → seznam dostupných pluginů
  „nainstaluj plugin X"                         → stáhne plugin z GitHubu
  „stáhni plugin X"                             → alias pro instalaci
  „install plugin X"                            → alias pro instalaci
  „nainstaluj z github user/repo"               → přímá instalace z GitHub URL
  „nainstaluj https://github.com/user/repo"     → přímá instalace z GitHub URL
  „odinstaluj plugin X"                         → smaže plugin složku
  „smaž plugin X"                               → alias pro odinstalaci
  „aktualizuj plugin X"                         → přestáhne plugin
  „update plugin X"                             → alias pro aktualizaci
"""

import re
import logging

logger = logging.getLogger(__name__)

# ── Patterny ──────────────────────────────────────────

_LIST_RE = re.compile(
    r"\b(marketplace\s+seznam|seznam\s+plugin[uů]|dostupn[eé]\s+pluginy)\b",
    re.IGNORECASE,
)

_INSTALL_RE = re.compile(
    r"\b(nainstaluj|sta[hž]ni|install)\s+plugin\s+([^\s,]+)",
    re.IGNORECASE,
)

_INSTALL_GH_RE = re.compile(
    r"\b(nainstaluj)\s+z\s+github\s+([\w.\-]+/[\w.\-]+)"
    r"|nainstaluj\s+(https?://github\.com/[\w.\-]+/[\w.\-]+)",
    re.IGNORECASE,
)

_UNINSTALL_RE = re.compile(
    r"\b(odinstaluj|sma[žz])\s+plugin\s+([^\s,]+)",
    re.IGNORECASE,
)

_UPDATE_RE = re.compile(
    r"\b(aktualizuj|update)\s+plugin\s+([^\s,]+)",
    re.IGNORECASE,
)


def _marketplace():
    from plugin_marketplace import PluginMarketplace
    return PluginMarketplace()


# ── Handlery ──────────────────────────────────────────

def _handle_list(text: str):
    result = _marketplace().list_available()
    return result, {"action": "answer", "params": {}}


def _handle_install(text: str):
    m = _INSTALL_RE.search(text)
    if not m:
        return None, None
    name = m.group(2).strip()
    result = _marketplace().install(name)
    return result, {"action": "answer", "params": {}}


def _handle_install_gh(text: str):
    m = _INSTALL_GH_RE.search(text)
    if not m:
        return None, None
    # Skupina 2 = user/repo bez URL, skupina 3 = plná URL
    repo = m.group(2) or m.group(3)
    if not repo:
        return None, None
    result = _marketplace().install_from_github(repo.strip())
    return result, {"action": "answer", "params": {}}


def _handle_uninstall(text: str):
    m = _UNINSTALL_RE.search(text)
    if not m:
        return None, None
    name = m.group(2).strip()
    result = _marketplace().uninstall(name)
    return result, {"action": "answer", "params": {}}


def _handle_update(text: str):
    m = _UPDATE_RE.search(text)
    if not m:
        return None, None
    name = m.group(2).strip()
    result = _marketplace().update(name)
    return result, {"action": "answer", "params": {}}


def get_routes():
    return [
        {"pattern": _INSTALL_GH_RE, "handler": _handle_install_gh},
        {"pattern": _LIST_RE,       "handler": _handle_list},
        {"pattern": _INSTALL_RE,    "handler": _handle_install},
        {"pattern": _UNINSTALL_RE,  "handler": _handle_uninstall},
        {"pattern": _UPDATE_RE,     "handler": _handle_update},
    ]


def get_actions():
    return {}
