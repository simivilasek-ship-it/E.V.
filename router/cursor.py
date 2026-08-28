"""Předání úkolu z E.V. do Cursor agenta."""
from __future__ import annotations

from cursor_bridge import extract_cursor_prompt


def route_cursor(text: str, t: str) -> tuple:
    prompt = extract_cursor_prompt(text, t)
    if prompt is None:
        return None, None
    if not prompt.strip():
        return "Jsem u Cursora. Řekni, co má udělat.", {"action": "answer", "params": {}}
    return (
        "Jdu za Cursorem. Předávám mu to.",
        {"action": "ask_cursor", "params": {"prompt": prompt}},
    )
