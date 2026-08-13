# Backward-compatible shim — implementation in router/
"""
E.V. — Lokální router (regex/fuzzy bez LLM)
Zpracovává 95% příkazů lokálně.

The LocalRouter class lives here for backward compatibility.
Domain implementations have been split into the router/ package:
  router/constants.py   — lookup tables and parse utilities
  router/apps.py        — route_apps, route_sites
  router/media.py       — route_music, route_vision
  router/system.py      — route_system, route_files
  router/memory_routes.py — route_memory
"""

import os
import re
from datetime import datetime

_HOME = os.path.expanduser("~")
_USER = os.environ.get("USER", os.path.basename(_HOME))

from commands.utils import normalize_text as _norm

# ── Re-export constants for backward compatibility ──────────────────────────
from router.constants import (
    _SITES, _APPS, _PROC_ALIASES,
    _MUSIC_STOP, _CLOSE_TRIGGER, _OPEN_TRIGGER,
    _FUZZY_COMMANDS, _FUZZY_THRESHOLD, _INSTALL_APP_NAMES,
    _parse_timer, _parse_move, _parse_translate,
    _parse_currency, _parse_reminder, _parse_memory_store,
)

# ── Domain routing functions ─────────────────────────────────────────────────
from router.apps import (
    route_apps, route_sites,
    _extract_app_name, _extract_install_name, _is_video_download_intent,
)
from router.media import route_music, route_vision
from router.system import route_system, route_files
from router.memory_routes import route_memory

try:
    from rapidfuzz import fuzz as _fuzz
    _HAS_FUZZY = True
except ImportError:
    _HAS_FUZZY = False


# ── parse_args kept here as a public utility ─────────────────────────────────
def _parse_args(command: str, args: str) -> dict:
    a = args.strip()
    try:
        m = {
            "open_app":       lambda: {"app": a},
            "open_url":       lambda: {"url": a if a.startswith("http") else "https://" + a},
            "search_web":     lambda: {"query": a},
            "write_text":     lambda: {"text": a},
            "type_key":       lambda: {"key": a},
            "kill_process":   lambda: {"name": a},
            "weather":        lambda: {"city": a},
            "vscode_open":    lambda: {"path": os.path.expanduser(a)},
            "open_file":      lambda: {"path": os.path.expanduser(a)},
            "create_folder":  lambda: {"path": os.path.expanduser(a)},
            "create_file":    lambda: {"path": os.path.expanduser(a)},
            "delete_file":    lambda: {"path": os.path.expanduser(a)},
            "install_app":    lambda: {"name": a},
            "uninstall_app":  lambda: {"name": a},
            "run_script":     lambda: {"path": os.path.expanduser(a)},
            "memory_recall":  lambda: {"query": a, "top_k": 5},
            "memory_store":   lambda: _parse_memory_store(a),
            "memory_stats":   lambda: {},
            "memory_maintenance": lambda: {},
            "clipboard_set":  lambda: {"text": a},
            "set_brightness": lambda: {"level": int(re.sub(r"[^\d]", "", a) or "50")},
            "volume":         lambda: {"level": int(a)} if a.isdigit()
                                      else {"action": a},
            "media":          lambda: {"action": a},
            "shutdown":       lambda: {"delay": int(re.sub(r"[^\d]", "", a) or "0")},
            "restart":        lambda: {"delay": int(re.sub(r"[^\d]", "", a) or "0")},
            "find_files":     lambda: {"name": a, "path": _HOME},
            "set_timer":      lambda: _parse_timer(a),
            "youtube_play":     lambda: {"query": a, "index": 1, "audio_only": False},
            "youtube_download": lambda: {"query": a, "audio_only": False, "quality": "best"},
            "youtube_info":     lambda: {"query": a},
            "youtube_subtitles":lambda: {"query": a, "lang": "cs"},
            "move_file":      lambda: _parse_move(a),
            "write_email":    lambda: {"to": a, "subject": "", "body": ""},
            "calculate":      lambda: {"expression": a},
            "translate":      lambda: _parse_translate(a),
            "note_add":       lambda: {"note": a},
            "note_list":      lambda: {},
            "reminder_set":   lambda: _parse_reminder(a),
            "wiki_search":    lambda: {"query": a},
            "currency_convert": lambda: _parse_currency(a),
        }
        if command in m:
            return m[command]()
    except Exception:
        pass
    return {}


# ══════════════════════════════════════════════════════
#  LOKÁLNÍ ROUTER — 95% příkazů bez LLM
# ══════════════════════════════════════════════════════

import logging
logger = logging.getLogger(__name__)

try:
    from router_dsl import RouterDSL as _RouterDSL
    _HAS_DSL = True
except ImportError:
    _HAS_DSL = False


class LocalRouter:
    """
    Zpracovává příkazy lokálně bez volání LLM.
    Vrátí (message, action_data) nebo (None, None) → jde na LLM.

    Personalizace webů: přidej `custom_sites` do config.json, např.:
        {"custom_sites": {"moodle": "https://moodle.your-school.cz"}}
    """

    def __init__(self):
        # Load custom site overrides from config.json
        try:
            from config import CONFIG
            custom_sites = CONFIG.get("custom_sites", {})
        except Exception:
            custom_sites = {}
        self._sites = {**_SITES, **custom_sites}

        if _HAS_DSL:
            self._dsl = _RouterDSL()
            self._dsl.rule('nastav hlasitost na {num}', 'volume', 'level', coerce=int)
            self._dsl.rule('hlasitost {num}', 'volume', 'level', coerce=int)
            self._dsl.rule('timer {num} minut', 'set_timer', 'seconds',
                           coerce=lambda x: int(float(x)) * 60)
            self._dsl.rule('timer {num} sekund', 'set_timer', 'seconds', coerce=int)
            self._dsl.rule('otevri {app}', 'open_app', 'app')
            self._dsl.rule('spust {app}', 'open_app', 'app')
        else:
            self._dsl = None

    def route(self, text: str) -> tuple:
        t  = _norm(text)
        dt = datetime.now()

        # DSL pre-check (saved for fallback — lower priority than regex)
        _dsl_result = (None, None)
        if self._dsl is not None:
            _dsl_action, _dsl_params = self._dsl.match(t)
            if _dsl_action is not None:
                _dsl_result = (None, {"action": _dsl_action, "params": _dsl_params})

        # Exact date shortcut — must run before sport/fuzzy ("dnes" alone ≠ sport)
        if re.search(r"^\s*(dnes|dneska|dnesni\s+datum)\s*$", t):
            return f"Dnes je {dt.strftime('%-d. %-m. %Y')}.", {"action": "get_date", "params": {}}

        # Apps: close trigger MUST run before fuzzy ("zavři X" ≠ "otevři X")
        result = route_apps(text, t, sites=self._sites)
        if result[1] is not None:
            return result

        # Exact substring match — higher priority than fuzzy
        for phrase, action, params_fn in _FUZZY_COMMANDS:
            if phrase in t:
                params = params_fn()
                if action == "get_time":
                    return f"Je {dt.strftime('%H:%M:%S')}.", {"action": action, "params": params}
                if action == "get_date":
                    return f"Dnes je {dt.strftime('%-d. %-m. %Y')}.", {"action": action, "params": params}
                return None, {"action": action, "params": params}

        # Fuzzy pre-pass (tolerates 1–2 typos)
        if _HAS_FUZZY and len(t) < 40:
            for phrase, action, params_fn in _FUZZY_COMMANDS:
                score = _fuzz.partial_ratio(t, phrase)
                if score >= _FUZZY_THRESHOLD:
                    logger.debug(f"Fuzzy match: '{t}' → '{phrase}' ({score})")
                    params = params_fn()
                    if action == "get_time":
                        return f"Je {dt.strftime('%H:%M:%S')}.", {"action": action, "params": params}
                    if action == "get_date":
                        return f"Dnes je {dt.strftime('%-d. %-m. %Y')}.", {"action": action, "params": params}
                    return None, {"action": action, "params": params}

        # Vision (screen describe, OCR, webcam)
        result = route_vision(text, t)
        if result[1] is not None:
            return result

        # System commands (time, date, hardware, disk, network, power, volume, etc.)
        result = route_system(text, t, dt)
        if result[1] is not None:
            return result

        # File / directory operations
        result = route_files(text, t)
        if result[1] is not None:
            return result

        # Site URL navigation (URL early + fallback URL)
        result = route_sites(text, t, sites=self._sites)
        if result[1] is not None:
            return result

        # Music / media playback
        result = route_music(text, t, sites=self._sites)
        if result[1] is not None:
            return result

        # Neural memory (recall / store / stats / maintenance)
        result = route_memory(text, t)
        if result[1] is not None:
            return result

        # DSL rules fallback (lower priority than all regex)
        if _dsl_result != (None, None):
            logger.debug(f"DSL match: '{t}' → {_dsl_result[1]}")
            return _dsl_result

        # Unrecognised → delegate to LLM
        return None, None


# Singleton
_router = LocalRouter()
