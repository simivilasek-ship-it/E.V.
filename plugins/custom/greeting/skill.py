"""E.V. Skill — Přivítání"""
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
    r"^\s*(?:ahoj|nazdar|čau|cau|zdravím|zdravim|"
    r"dobrý\s+den|dobry\s+den|dobré\s+ráno|dobre\s+rano|"
    r"dobré\s+odpoledne|dobre\s+odpoledne)"
    r"(?:\s+[A-Za-zÁ-ž]{2,16})?\s*[!.]*\s*$",
    re.IGNORECASE | re.UNICODE,
)
_GOODBYE_RE = re.compile(
    r"^\s*(?:nashle|na\s+shledanou|čau\s+čau|cau\s+cau|bye|goodbye|dobrou\s+noc)\s*[!.]*\s*$",
    re.IGNORECASE | re.UNICODE,
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
