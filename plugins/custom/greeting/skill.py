"""JARVIS Skill — Přivítání"""
import re
import random
from datetime import datetime

_GREETINGS = [
    "Jak ti mohu dnes pomoci?",
    "Jsem připraven.",
    "Co pro tebe udělám?",
    "Vítej zpět! Co potřebuješ?",
]
_GOODBYES = [
    "Na shledanou! Stačí zavolat.",
    "Nashle! Budu tady, až mě budeš potřebovat.",
    "Čau! Hodně zdaru.",
]

_GREETING_RE = re.compile(
    r"\b(ahoj|nazdar|cau|zdravim|dobry\s+den|dobre\s+rano|dobre\s+odpoledne|dobrou\s+noc)\b",
    re.IGNORECASE,
)
_GOODBYE_RE = re.compile(
    r"\b(nashle|na\s+shledanou|cau|bye|goodbye|dobrou\s+noc)\b",
    re.IGNORECASE,
)


def _handle_greeting(text: str):
    hour = datetime.now().hour
    if hour < 12:
        prefix = "Dobré ráno!"
    elif hour < 18:
        prefix = "Dobrý den!"
    else:
        prefix = "Dobrý večer!"
    return f"{prefix} {random.choice(_GREETINGS)}", {"action": "answer", "params": {}}


def _handle_goodbye(text: str):
    return random.choice(_GOODBYES), {"action": "answer", "params": {}}


def get_routes():
    return [
        {"pattern": _GOODBYE_RE, "handler": _handle_goodbye},
        {"pattern": _GREETING_RE, "handler": _handle_greeting},
    ]


def get_actions():
    return {}
