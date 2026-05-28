"""
JARVIS — Security 2.0
Audit log, úrovně oprávnění, detekce nebezpečných patternů, sandbox.
"""

from __future__ import annotations
import logging
import re
import time
import json
import threading
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)


# ── Úrovně oprávnění ──────────────────────────────────

class PermissionLevel(Enum):
    SAFE        = 0   # vždy povoleno
    STANDARD    = 1   # vyžaduje ověření uživatele
    ELEVATED    = 2   # vyžaduje explicitní potvrzení
    RESTRICTED  = 3   # blokováno ve výchozím stavu
    FORBIDDEN   = 4   # vždy zakázáno


# Mapování akcí na úrovně oprávnění
ACTION_PERMISSIONS: Dict[str, PermissionLevel] = {
    # SAFE — vždy povoleno
    "answer":           PermissionLevel.SAFE,
    "clear_history":    PermissionLevel.SAFE,
    "get_time":         PermissionLevel.SAFE,
    "get_date":         PermissionLevel.SAFE,
    "system_info":      PermissionLevel.SAFE,
    "weather":          PermissionLevel.SAFE,
    "search_web":       PermissionLevel.SAFE,
    "open_url":         PermissionLevel.SAFE,
    "open_app":         PermissionLevel.SAFE,
    "youtube_play":     PermissionLevel.SAFE,
    "youtube_info":     PermissionLevel.SAFE,
    "screenshot":       PermissionLevel.SAFE,
    "screen_describe":  PermissionLevel.SAFE,
    "screen_ocr":       PermissionLevel.SAFE,
    "webcam_describe":  PermissionLevel.STANDARD,
    "volume":           PermissionLevel.SAFE,
    "media":            PermissionLevel.SAFE,
    "set_brightness":   PermissionLevel.SAFE,
    "set_timer":        PermissionLevel.SAFE,
    "wiki_search":      PermissionLevel.SAFE,
    "note_add":         PermissionLevel.SAFE,
    "note_list":        PermissionLevel.SAFE,
    "clipboard_set":    PermissionLevel.SAFE,
    "write_text":       PermissionLevel.SAFE,
    "type_key":         PermissionLevel.SAFE,
    "find_files":       PermissionLevel.SAFE,
    "open_file":        PermissionLevel.SAFE,
    "vscode_open":      PermissionLevel.SAFE,
    "calculate":        PermissionLevel.SAFE,
    "translate":        PermissionLevel.SAFE,
    "memory_recall":    PermissionLevel.SAFE,
    "memory_stats":     PermissionLevel.SAFE,
    "write_email":      PermissionLevel.SAFE,
    "youtube_download": PermissionLevel.SAFE,
    "youtube_subtitles":PermissionLevel.SAFE,
    # STANDARD — potvrzení dialogem
    "create_folder":    PermissionLevel.STANDARD,
    "create_file":      PermissionLevel.STANDARD,
    "move_file":        PermissionLevel.STANDARD,
    "memory_store":     PermissionLevel.STANDARD,
    "memory_maintenance":PermissionLevel.STANDARD,
    "vscode_new_file":  PermissionLevel.STANDARD,
    # ELEVATED — explicitní potvrzení
    "delete_file":      PermissionLevel.ELEVATED,
    "kill_process":     PermissionLevel.ELEVATED,
    "install_app":      PermissionLevel.ELEVATED,
    "uninstall_app":    PermissionLevel.ELEVATED,
    "run_script":       PermissionLevel.ELEVATED,
    "shutdown":         PermissionLevel.ELEVATED,
    "restart":          PermissionLevel.ELEVATED,
    "sleep_pc":         PermissionLevel.ELEVATED,
    "update_system":    PermissionLevel.ELEVATED,
}

# Nebezpečné patterny v textu příkazů
DANGEROUS_PATTERNS = [
    r"rm\s+-rf",
    r"sudo\s+rm",
    r"format\s+[a-z]:",
    r"dd\s+if=",
    r"mkfs\.",
    r":(){ :|:& };:",   # fork bomb
    r">\s*/dev/sda",
    r"chmod\s+777\s+/",
]

_DANGEROUS_RE = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]


# ── Audit Log ─────────────────────────────────────────

@dataclass
class AuditEntry:
    timestamp:  float
    action:     str
    params:     Dict[str, Any]
    allowed:    bool
    reason:     str
    user_text:  str = ""
    result:     str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AuditLog:
    """Persistentní audit log všech akcí."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path: Path = path or Path.home() / ".jarvis_audit.jsonl"
        self._entries: List[AuditEntry] = []
        self._lock: threading.Lock = threading.Lock()
        self._ensure_secure_file()
        self._load_recent()

    def _ensure_secure_file(self) -> None:
        """Vytvoří soubor s oprávněními 0o600 (čte jen vlastník)."""
        import os
        if not self._path.exists():
            try:
                self._path.touch(mode=0o600)
            except Exception as e:
                logger.warning(f"Audit log: nelze nastavit oprávnění: {e}")
        else:
            try:
                os.chmod(self._path, 0o600)
            except Exception as e:
                logger.warning(f"Audit log chmod: {e}")

    def log(self, action: str, params: Dict[str, Any], allowed: bool,
            reason: str = "", user_text: str = "", result: str = "") -> None:
        """Záznam akce do audit logu"""
        entry: AuditEntry = AuditEntry(
            timestamp=time.time(), action=action, params=params,
            allowed=allowed, reason=reason, user_text=user_text, result=result,
        )
        with self._lock:
            self._entries.append(entry)
            # Piš do souboru
            try:
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
            except Exception as e:
                logger.warning(f"Audit log chyba: {e}")

    def get_recent(self, limit: int = 50) -> List[AuditEntry]:
        """Vrátí posledních N záznamů"""
        with self._lock:
            return self._entries[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Vrátí statistiky audit logu"""
        with self._lock:
            total: int = len(self._entries)
            blocked: int = sum(1 for e in self._entries if not e.allowed)
            by_action: Dict[str, int] = {}
            for e in self._entries:
                by_action[e.action] = by_action.get(e.action, 0) + 1
        return {"total": total, "blocked": blocked, "by_action": by_action}

    def _load_recent(self) -> None:
        """Načte posledních 1000 záznamů ze souboru."""
        try:
            if self._path.exists():
                lines: List[str] = self._path.read_text(encoding="utf-8").strip().split("\n")
                for line in lines[-1000:]:
                    if line:
                        d: Dict[str, Any] = json.loads(line)
                        self._entries.append(AuditEntry(**d))
        except Exception:
            pass


# ── Security Manager ──────────────────────────────────

class SecurityManager:
    """Hlavní bezpečnostní vrstva JARVIS 2.0."""

    def __init__(self, max_permission: PermissionLevel = PermissionLevel.ELEVATED) -> None:
        self._max_permission: PermissionLevel = max_permission
        self._audit: AuditLog = AuditLog()
        self._whitelist: Set[str] = set()
        self._blacklist: Set[str] = set()

    def check(self, action: str, params: Dict[str, Any],
              user_text: str = "") -> tuple[bool, str]:
        """
        Zkontroluje zda je akce povolena.
        Vrátí (allowed, reason).
        """
        # Blacklist má přednost
        if action in self._blacklist:
            reason = f"Akce '{action}' je v blacklistu"
            self._audit.log(action, params, False, reason, user_text)
            return False, reason

        # Kontrola nebezpečných patternů v parametrech
        param_str = str(params)
        for pattern in _DANGEROUS_RE:
            if pattern.search(param_str):
                reason = f"Nebezpečný vzor detekován v parametrech"
                self._audit.log(action, params, False, reason, user_text)
                return False, reason

        # Whitelist
        if action in self._whitelist:
            self._audit.log(action, params, True, "whitelist", user_text)
            return True, "whitelist"

        # Kontrola úrovně oprávnění
        level = ACTION_PERMISSIONS.get(action)
        if level is None:
            reason = f"Neznámá akce: {action}"
            self._audit.log(action, params, False, reason, user_text)
            return False, reason

        if level == PermissionLevel.FORBIDDEN:
            reason = "Akce je zakázána"
            self._audit.log(action, params, False, reason, user_text)
            return False, reason

        if level.value > self._max_permission.value:
            reason = f"Nedostatečná oprávnění (vyžaduje {level.name})"
            self._audit.log(action, params, False, reason, user_text)
            return False, reason

        self._audit.log(action, params, True, level.name, user_text)
        return True, level.name

    def needs_confirmation(self, action: str) -> bool:
        level = ACTION_PERMISSIONS.get(action, PermissionLevel.RESTRICTED)
        return level in (PermissionLevel.ELEVATED, PermissionLevel.RESTRICTED)

    def add_to_whitelist(self, action: str):
        self._whitelist.add(action)

    def add_to_blacklist(self, action: str):
        self._blacklist.add(action)

    def get_audit_log(self, limit: int = 50) -> List[Dict]:
        return [e.to_dict() for e in self._audit.get_recent(limit)]

    def get_stats(self) -> Dict:
        return self._audit.get_stats()


# Typový hint
from typing import Tuple

# ── Potvrzovací dialog ────────────────────────────────

def confirm_action(action: str, params: Dict[str, Any], parent=None) -> bool:
    """Zobrazí dialog pro potvrzení nebezpečné akce."""
    level = ACTION_PERMISSIONS.get(action, PermissionLevel.RESTRICTED)
    if level not in (PermissionLevel.ELEVATED, PermissionLevel.RESTRICTED):
        return True

    try:
        import tkinter.messagebox as msgbox
        prompt = f"Opravdu chcete provést akci '{action}'?"
        if params:
            details = ", ".join(f"{k}={v}" for k, v in params.items())
            prompt += f"\n{details}"
        return msgbox.askyesno("Potvrzení akce", prompt, parent=parent)
    except Exception as e:
        logger.warning(f"Dialog potvrzení selhal: {e}")
        return False


# ── Singleton ─────────────────────────────────────────

_security: Optional[SecurityManager] = None


def get_security_manager() -> SecurityManager:
    global _security
    if _security is None:
        _security = SecurityManager()
    return _security


# ── Kompatibilní aliasy (nahrazují starý security.py) ──

@dataclass
class AuditLogEntry:
    """Jednoduchá datová třída pro testy a kompatibilitu."""
    action: str
    user: str = ""
    status: str = "success"
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: Any = field(default_factory=lambda: __import__("datetime").datetime.now())


def requires_confirmation(action: str, params: Dict[str, Any] = None) -> bool:
    """Vrátí True pokud akce vyžaduje potvrzení."""
    level = ACTION_PERMISSIONS.get(action, PermissionLevel.RESTRICTED)
    return level in (PermissionLevel.ELEVATED, PermissionLevel.RESTRICTED)


def contains_dangerous_pattern(text: str) -> bool:
    """Vrátí True pokud text obsahuje nebezpečný vzor."""
    return any(p.search(text) for p in _DANGEROUS_RE)


def is_action_allowed(action: str) -> bool:
    """Modul-level alias — zkontroluje zda je akce povolena."""
    allowed, _ = get_security_manager().check(action, {})
    return allowed


# Aliasy na SecurityManager metodách
SecurityManager.is_action_allowed = lambda self, action: self.check(action, {})[0]
SecurityManager.log_action = lambda self, action, user="", status="success", details=None: \
    self._audit.log(action, details or {}, status == "success", status, user)

try:
    from error_handling import ErrorCategory  # re-export pro zpětnou kompatibilitu testů
except ImportError:
    pass
