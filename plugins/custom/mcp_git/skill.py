"""
E.V. Skill — MCP Git
Čtení a analýza git repozitářů přes MCP server.
Bez API klíče — pracuje s lokálními repozitáři.

Příkazy:
  „git log ~/Projekty/jarvis"     → posledních 10 commitů
  „git status ~/Projekty/app"     → aktuální stav repozitáře
  „git diff ~/Projekty/app"       → neuložené změny
  „větve v ~/Projekty/app"        → seznam větví
  „git blame ~/Projekty/app/main.py" → kdo napsal každý řádek
"""

import re
import os
import logging

logger = logging.getLogger(__name__)

_bridge = None
_DEFAULT_REPO = os.path.expanduser("~/Stažené/nepojmenovaná složka")  # E.V. repo


def _get_bridge():
    global _bridge
    if _bridge is None:
        try:
            from mcp_bridge import get_mcp_bridge
            _bridge = get_mcp_bridge()
        except Exception as e:
            logger.warning(f"MCP git bridge nedostupný: {e}")
    return _bridge


def _available() -> bool:
    b = _get_bridge()
    return b is not None and b.is_available("git")


def _call(tool: str, args: dict) -> str:
    result = _get_bridge().call_tool("git", tool, args)
    if not result:
        return "(prázdný výsledek)"
    if len(result) > 3000:
        result = result[:3000] + "\n…(zkráceno)"
    return result


def _extract_repo(text: str) -> str:
    """Extrahuje cestu k repozitáři z textu, nebo vrátí výchozí."""
    m = re.search(r"(~/[\w/.\-]+|/[\w/.\-]+)", text)
    if m:
        return os.path.expanduser(m.group(1))
    return _DEFAULT_REPO


# ── Patterny ──────────────────────────────────────────

_LOG_RE    = re.compile(r"\b(git\s+log|commit[yů]|historie\s+commitu)\b", re.IGNORECASE)
_STATUS_RE = re.compile(r"\b(git\s+status|stav\s+repozitare)\b", re.IGNORECASE)
_DIFF_RE   = re.compile(r"\b(git\s+diff|zmeny|neulozen[eé]\s+zmeny)\b", re.IGNORECASE)
_BRANCH_RE = re.compile(r"\b(vetv[ei]|branch[e]?|git\s+branch)\b", re.IGNORECASE)
_BLAME_RE  = re.compile(r"\b(git\s+blame|kdo\s+napsal)\b.{0,20}?([\w/~.\-]+\.[\w]+)", re.IGNORECASE)
_SEARCH_COMMITS_RE = re.compile(
    r"\b(hledej\s+commit|search\s+commit)\b\s+[\"']?(.+?)[\"']?\s*(?:v\s+)?([~/\w.\-]*)",
    re.IGNORECASE,
)


def _handle_log(text: str):
    if not _available():
        return "MCP Git není dostupný.", {"action": "answer", "params": {}}
    repo = _extract_repo(text)
    result = _call("git_log", {"repo_path": repo, "max_count": 10})
    return f"**Git log** `{repo}`:\n```\n{result}\n```", {"action": "answer", "params": {}}


def _handle_status(text: str):
    if not _available():
        return "MCP Git není dostupný.", {"action": "answer", "params": {}}
    repo = _extract_repo(text)
    result = _call("git_status", {"repo_path": repo})
    return f"**Git status** `{repo}`:\n```\n{result}\n```", {"action": "answer", "params": {}}


def _handle_diff(text: str):
    if not _available():
        return "MCP Git není dostupný.", {"action": "answer", "params": {}}
    repo = _extract_repo(text)
    result = _call("git_diff", {"repo_path": repo})
    if not result.strip() or result == "(prázdný výsledek)":
        return "Žádné neuložené změny.", {"action": "answer", "params": {}}
    return f"**Git diff** `{repo}`:\n```diff\n{result}\n```", {"action": "answer", "params": {}}


def _handle_branches(text: str):
    if not _available():
        return "MCP Git není dostupný.", {"action": "answer", "params": {}}
    repo = _extract_repo(text)
    result = _call("git_branch", {"repo_path": repo})
    return f"**Větve** `{repo}`:\n```\n{result}\n```", {"action": "answer", "params": {}}


def _handle_blame(text: str):
    m = _BLAME_RE.search(text)
    if not m:
        return None, None
    if not _available():
        return "MCP Git není dostupný.", {"action": "answer", "params": {}}
    file_path = os.path.expanduser(m.group(2).strip())
    repo = _extract_repo(text)
    result = _call("git_blame", {"repo_path": repo, "file_path": file_path})
    return f"**Git blame** `{file_path}`:\n```\n{result}\n```", {"action": "answer", "params": {}}


def _handle_search_commits(text: str):
    m = _SEARCH_COMMITS_RE.search(text)
    if not m:
        return None, None
    if not _available():
        return "MCP Git není dostupný.", {"action": "answer", "params": {}}
    query = m.group(2).strip()
    repo = os.path.expanduser(m.group(3).strip()) if m.group(3) else _DEFAULT_REPO
    result = _call("git_search_commits", {"repo_path": repo, "query": query})
    return f"**Commity s '{query}'**:\n```\n{result}\n```", {"action": "answer", "params": {}}


def get_routes():
    return [
        {"pattern": _BLAME_RE,          "handler": _handle_blame},
        {"pattern": _SEARCH_COMMITS_RE, "handler": _handle_search_commits},
        {"pattern": _LOG_RE,            "handler": _handle_log},
        {"pattern": _STATUS_RE,         "handler": _handle_status},
        {"pattern": _DIFF_RE,           "handler": _handle_diff},
        {"pattern": _BRANCH_RE,         "handler": _handle_branches},
    ]


def get_actions():
    return {}
