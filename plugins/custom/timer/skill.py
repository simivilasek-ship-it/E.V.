"""E.V. Skill — Časovač"""
import re
import threading
import time
import logging

logger = logging.getLogger(__name__)

_TIMER_RE = re.compile(
    r"\b(timer|casovac|alarm|odpocitej|odpocet)\b.*?(\d+)\s*(sekund|sec|s\b|minut|min|m\b|hodin|hod|h\b)",
    re.IGNORECASE,
)
_TIMER_SIMPLE = re.compile(
    r"\b(za|po)\s+(\d+)\s*(sekund|sec|minut|min|hodin|hod)\b",
    re.IGNORECASE,
)

_UNIT_MULT = {
    "s": 1, "sec": 1, "sekund": 1,
    "m": 60, "min": 60, "minut": 60,
    "h": 3600, "hod": 3600, "hodin": 3600,
}

_on_timer_done = None  # Callback nastavený při registraci


def _parse_seconds(amount: int, unit: str) -> int:
    for key, mult in _UNIT_MULT.items():
        if unit.lower().startswith(key):
            return amount * mult
    return amount * 60


def _start_timer(seconds: int, label: str = "Timer"):
    def _run():
        time.sleep(seconds)
        msg = f"⏰ {label} — čas vypršel!"
        logger.info(msg)
        if _on_timer_done:
            _on_timer_done(msg)
    threading.Thread(target=_run, daemon=True).start()


def _handle_timer(text: str):
    m = _TIMER_RE.search(text) or _TIMER_SIMPLE.search(text)
    if not m:
        return None, None

    groups = m.groups()
    # Najdi číslo a jednotku v groups
    amount = unit = None
    for g in groups:
        if g and g.isdigit():
            amount = int(g)
        elif g and not g.isdigit() and g.lower() not in ("timer", "casovac", "alarm",
                                                           "odpocitej", "odpocet", "za", "po"):
            unit = g

    if amount is None or unit is None:
        return None, None

    seconds = _parse_seconds(amount, unit)
    _start_timer(seconds, f"Timer {amount} {unit}")

    if seconds < 60:
        label = f"{seconds} sekund"
    elif seconds < 3600:
        label = f"{seconds // 60} minut"
    else:
        label = f"{seconds // 3600} hodin"

    return f"Timer nastaven na {label}.", {"action": "set_timer",
                                           "params": {"seconds": seconds, "label": "Timer"}}


def get_routes():
    return [
        {"pattern": _TIMER_RE, "handler": _handle_timer},
        {"pattern": _TIMER_SIMPLE, "handler": _handle_timer},
    ]


def get_actions():
    return {}
