"""UI automation commands (Computer Use via accessibility APIs)."""

from __future__ import annotations

from computer_use import ui_tree, ui_click, ui_set_value
from config import CONFIG


def cmd_ui_tree(max_nodes: int = 400) -> str:
    if not bool(CONFIG.get("computer_use_enabled", False)):
        return "Computer Use je vypnuté (computer_use_enabled=false)."
    return ui_tree(CONFIG, max_nodes=int(max_nodes))


def cmd_ui_click(text: str = "", role: str = "") -> str:
    if not bool(CONFIG.get("computer_use_enabled", False)):
        return "Computer Use je vypnuté (computer_use_enabled=false)."
    if not text.strip():
        return "Zadej text/label elementu."
    return ui_click(text.strip(), CONFIG, role=role.strip() or None)


def cmd_ui_set_value(text: str = "", value: str = "", role: str = "") -> str:
    if not bool(CONFIG.get("computer_use_enabled", False)):
        return "Computer Use je vypnuté (computer_use_enabled=false)."
    if not text.strip():
        return "Zadej text/label elementu."
    return ui_set_value(text.strip(), value or "", CONFIG, role=role.strip() or None)
