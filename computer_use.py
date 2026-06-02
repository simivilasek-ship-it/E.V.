"""Computer Use — OS accessibility / UI automation (MVP)

This module provides a cross-platform abstraction to query UI element trees and
invoke actions without relying on screenshots + coordinate guessing.

Backends (optional):
- Windows: UI Automation (UIA) via pywinauto/uiautomation
- macOS: Accessibility API via PyObjC
- Linux: AT-SPI via pyatspi

This is an MVP scaffold: it exposes stable interfaces and safe fallbacks.
"""

from __future__ import annotations

import logging
import platform
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class UIElement:
    id: str
    role: str
    name: str = ""
    value: str = ""
    children: List["UIElement"] = field(default_factory=list)


class UIAutomationBackend:
    """Backend interface."""

    name: str = "base"

    def available(self) -> bool:
        return False

    def get_active_window_tree(self, max_nodes: int = 400) -> UIElement:
        return UIElement(id="root", role="root", name="")

    def invoke(self, element_id: str) -> bool:
        return False

    def set_value(self, element_id: str, text: str) -> bool:
        return False


class LinuxATSPIBackend(UIAutomationBackend):
    name = "linux_atspi"

    def __init__(self):
        self._atspi = None
        self._node_map: Dict[str, Any] = {}
        try:
            import pyatspi  # type: ignore

            self._atspi = pyatspi
        except Exception:
            self._atspi = None

    def available(self) -> bool:
        return self._atspi is not None

    def get_active_window_tree(self, max_nodes: int = 400) -> UIElement:
        if not self._atspi:
            return super().get_active_window_tree(max_nodes=max_nodes)

        try:
            desktop = self._atspi.Registry.getDesktop(0)
            root = UIElement(id="root", role="desktop", name="desktop")
            self._node_map.clear()
            count = 0

            def walk(acc, parent: UIElement):
                nonlocal count
                if count >= max_nodes:
                    return
                try:
                    role = str(acc.getRoleName() or "")
                    name = str(acc.name or "")
                    eid = f"{id(acc)}"
                    node = UIElement(id=eid, role=role, name=name)
                    self._node_map[eid] = acc
                    parent.children.append(node)
                    count += 1
                    for i in range(int(acc.childCount)):
                        if count >= max_nodes:
                            break
                        walk(acc.getChildAtIndex(i), node)
                except Exception:
                    return

            for i in range(int(desktop.childCount)):
                if count >= max_nodes:
                    break
                app = desktop.getChildAtIndex(i)
                walk(app, root)
            return root
        except Exception as e:
            logger.debug(f"AT-SPI tree failed: {e}")
            return super().get_active_window_tree(max_nodes=max_nodes)

    def invoke(self, element_id: str) -> bool:
        if not self._atspi:
            return False
        acc = self._node_map.get(element_id)
        if acc is None:
            return False
        try:
            if hasattr(acc, "doAction"):
                return bool(acc.doAction(0))
        except Exception:
            pass
        try:
            # Some AT-SPI objects expose actions through getAction and doAction
            if getattr(acc, "action", None):
                return bool(acc.action.doAction(0))
        except Exception:
            pass
        return False

    def set_value(self, element_id: str, text: str) -> bool:
        if not self._atspi:
            return False
        acc = self._node_map.get(element_id)
        if acc is None:
            return False
        try:
            if hasattr(acc, "setTextContents"):
                acc.setTextContents(str(text))
                return True
            if hasattr(acc, "text") and hasattr(acc.text, "setTextContents"):
                acc.text.setTextContents(str(text))
                return True
            if getattr(acc, "value", None) and hasattr(acc.value, "setCurrentValue"):
                acc.value.setCurrentValue(str(text))
                return True
        except Exception:
            pass
        return False


class WindowsUIABackend(UIAutomationBackend):
    name = "windows_uia"

    def __init__(self):
        self._available = False
        self._client = None
        try:
            import uiautomation as ui  # type: ignore
            self._client = ui
            self._available = True
        except Exception:
            self._available = False

    def available(self) -> bool:
        return self._available

    def get_active_window_tree(self, max_nodes: int = 400) -> UIElement:
        return super().get_active_window_tree(max_nodes=max_nodes)


class MacOSAXBackend(UIAutomationBackend):
    name = "macos_ax"

    def __init__(self):
        self._available = False
        try:
            import objc  # type: ignore
            import AppKit  # type: ignore
            self._available = True
        except Exception:
            self._available = False

    def available(self) -> bool:
        return self._available

    def get_active_window_tree(self, max_nodes: int = 400) -> UIElement:
        return super().get_active_window_tree(max_nodes=max_nodes)


class NullBackend(UIAutomationBackend):
    name = "none"

    def available(self) -> bool:
        return False


_backend_singleton: Optional[UIAutomationBackend] = None


def get_ui_backend(config: Optional[dict] = None) -> UIAutomationBackend:
    global _backend_singleton
    if _backend_singleton is not None:
        return _backend_singleton

    cfg = config or {}
    forced = str(cfg.get("computer_use_backend", "auto"))
    system = platform.system()

    candidates: List[UIAutomationBackend] = []

    if forced in ("linux_atspi", "auto") and system == "Linux":
        candidates.append(LinuxATSPIBackend())
    if forced in ("windows_uia", "auto") and system == "Windows":
        candidates.append(WindowsUIABackend())
    if forced in ("macos_ax", "auto") and system == "Darwin":
        candidates.append(MacOSAXBackend())

    for c in candidates:
        if c.available():
            _backend_singleton = c
            logger.info(f"ComputerUse backend: {c.name}")
            return c

    _backend_singleton = NullBackend()
    logger.info("ComputerUse backend: none")
    return _backend_singleton


def format_tree(root: UIElement, max_depth: int = 6) -> str:
    lines: List[str] = []

    def rec(n: UIElement, depth: int):
        if depth > max_depth:
            return
        indent = "  " * depth
        label = n.name.strip()[:60]
        lines.append(f"{indent}- {n.role}{': ' + label if label else ''} (id={n.id})")
        for ch in n.children[:50]:
            rec(ch, depth + 1)

    rec(root, 0)
    return "\n".join(lines)


def find_by_text(root: UIElement, text: str, role: Optional[str] = None) -> Optional[UIElement]:
    t = text.lower().strip()
    role_l = role.lower().strip() if role else None

    best: Optional[UIElement] = None

    def rec(n: UIElement):
        nonlocal best
        if best is not None:
            return
        if role_l and n.role.lower() != role_l:
            pass
        if t and t in (n.name or "").lower():
            if role_l is None or n.role.lower() == role_l:
                best = n
                return
        for ch in n.children:
            rec(ch)

    rec(root)
    return best


def ui_tree(config: Optional[dict] = None, max_nodes: int = 400) -> str:
    backend = get_ui_backend(config)
    if not backend.available():
        return "Computer Use není dostupné (backend nenalezen)."
    root = backend.get_active_window_tree(max_nodes=max_nodes)
    return format_tree(root)


def ui_click(selector_text: str, config: Optional[dict] = None, role: Optional[str] = None) -> str:
    backend = get_ui_backend(config)
    if not backend.available():
        return "Computer Use není dostupné (backend nenalezen)."

    tree = backend.get_active_window_tree(max_nodes=500)
    el = find_by_text(tree, selector_text, role=role)
    if not el:
        return f"Nenalezeno: {selector_text!r}"

    ok = backend.invoke(el.id)
    return "ok" if ok else "Akci nelze provést (invoke selhalo nebo není podporováno)."


def ui_set_value(selector_text: str, value: str, config: Optional[dict] = None, role: Optional[str] = None) -> str:
    backend = get_ui_backend(config)
    if not backend.available():
        return "Computer Use není dostupné (backend nenalezen)."

    tree = backend.get_active_window_tree(max_nodes=500)
    el = find_by_text(tree, selector_text, role=role)
    if not el:
        return f"Nenalezeno: {selector_text!r}"

    ok = backend.set_value(el.id, value)
    return "ok" if ok else "Nastavení hodnoty selhalo nebo není podporováno."