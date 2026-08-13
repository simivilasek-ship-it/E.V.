"""E.V. Skill — Schránka"""
import re
import subprocess
import logging

logger = logging.getLogger(__name__)

_COPY_RE = re.compile(
    r"\b(zkopiruj|zkopirovat|copy)\b\s+(.+)",
    re.IGNORECASE,
)
_PASTE_RE = re.compile(
    r"\b(vloz|paste|co\s+(je\s+)?(ve\s+)?schranc[ei]|clipboard)\b",
    re.IGNORECASE,
)


def _xclip_available() -> bool:
    try:
        result = subprocess.run(["which", "xclip"], capture_output=True)
        return result.returncode == 0
    except Exception:
        return False


def _set_clipboard(text: str) -> bool:
    try:
        proc = subprocess.Popen(["xclip", "-selection", "clipboard"],
                                stdin=subprocess.PIPE)
        proc.communicate(text.encode())
        return True
    except Exception:
        try:
            import pyperclip
            pyperclip.copy(text)
            return True
        except Exception:
            return False


def _get_clipboard() -> str:
    try:
        result = subprocess.run(["xclip", "-selection", "clipboard", "-o"],
                                capture_output=True, text=True)
        return result.stdout.strip()
    except Exception:
        try:
            import pyperclip
            return pyperclip.paste()
        except Exception:
            return ""


def _handle_copy(text: str):
    m = _COPY_RE.search(text)
    if not m:
        return None, None
    content = m.group(2).strip()
    if _set_clipboard(content):
        return f"Zkopírováno: {content[:50]}", {"action": "clipboard_set",
                                                  "params": {"text": content}}
    return "Schránka není dostupná.", {"action": "answer", "params": {}}


def _handle_paste(text: str):
    content = _get_clipboard()
    if content:
        return f"Ve schránce: {content[:100]}", {"action": "answer", "params": {}}
    return "Schránka je prázdná.", {"action": "answer", "params": {}}


def get_routes():
    return [
        {"pattern": _COPY_RE, "handler": _handle_copy},
        {"pattern": _PASTE_RE, "handler": _handle_paste},
    ]


def get_actions():
    return {}
