"""
JARVIS Plugin — Přivítání
Ukázkový plugin který reaguje na pozdravy a vrací vlastní odpovědi.

Instalace: uložte do plugins/custom/ — JARVIS načte automaticky.
"""

import re
import random
from datetime import datetime

PLUGIN_NAME = "greeting"
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = "JARVIS"


_GREETINGS = [
    "Ahoj! Jak ti mohu dnes pomoci?",
    "Zdravím! Jsem připraven.",
    "Dobrý den! Co pro tebe udělám?",
    "Vítej zpět! Co potřebuješ?",
]

_GOODBYES = [
    "Na shledanou! Stačí zavolat.",
    "Nashle! Budu tady, až mě budeš potřebovat.",
    "Čau! Hodně zdaru.",
]

_GREETING_RE = re.compile(
    r"\b(ahoj|nazdar|čau|zdravím|dobrý\s+den|dobré\s+ráno|dobré\s+odpoledne|dobrou\s+noc)\b",
    re.IGNORECASE,
)
_GOODBYE_RE = re.compile(
    r"\b(nashle|na\s+shledanou|čau|bye|goodbye|dobrou\s+noc)\b",
    re.IGNORECASE,
)


def _handle_greeting(text: str):
    hour = datetime.now().hour
    if hour < 12:
        time_part = "Dobré ráno!"
    elif hour < 18:
        time_part = "Dobrý den!"
    else:
        time_part = "Dobrý večer!"
    reply = f"{time_part} {random.choice(_GREETINGS)}"
    return reply, {"action": "answer", "params": {}}


def _handle_goodbye(text: str):
    return random.choice(_GOODBYES), {"action": "answer", "params": {}}


def get_routes():
    """Vrátí seznam route pravidel pro plugin."""
    return [
        {"pattern": _GOODBYE_RE, "handler": _handle_goodbye},
        {"pattern": _GREETING_RE, "handler": _handle_greeting},
    ]


def get_actions():
    """Vrátí slovník akcí které plugin implementuje."""
    return {}
