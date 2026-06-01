"""
JARVIS Global Hotkey — Alt+Space kdekoliv v OS vyvolá quick input.
Funguje na Linuxu přes pynput nebo keyboard lib.
Opt-in: pokud lib chybí, molly gracefully.
"""
from __future__ import annotations
import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class GlobalHotkey:
    """Registruje globální klávesovou zkratku Alt+Space.

    Při stisku zavolá callback(text) kde text je to co uživatel napsal.
    Implementováno přes pynput (Linux X11/Wayland).
    """

    DEFAULT_HOTKEY = "<alt>+<space>"

    def __init__(self, callback: Callable[[str], None],
                 hotkey: str = DEFAULT_HOTKEY):
        self._callback = callback
        self._hotkey   = hotkey
        self._listener = None
        self._running  = False
        self._available = False

        try:
            import pynput
            self._available = True
        except ImportError:
            logger.info("GlobalHotkey: pynput není nainstalován — zkus: pip install pynput")

    @property
    def available(self) -> bool:
        return self._available

    def start(self) -> bool:
        """Spustí posluchač klávesnice. Vrátí True pokud se podařilo."""
        if not self._available:
            return False
        if self._running:
            return True

        try:
            from pynput import keyboard

            def on_activate():
                logger.debug("GlobalHotkey aktivován")
                # Zobraz mini quick-input dialog
                self._show_quick_input()

            self._listener = keyboard.GlobalHotKeys({
                self._hotkey: on_activate
            })
            self._listener.start()
            self._running = True
            logger.info(f"GlobalHotkey spuštěn: {self._hotkey}")
            return True
        except Exception as e:
            logger.warning(f"GlobalHotkey start selhal: {e}")
            return False

    def stop(self) -> None:
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
        self._running = False
        self._listener = None

    def _show_quick_input(self) -> None:
        """Zobrazí minimalistické Tkinter okno pro rychlý vstup."""
        threading.Thread(target=self._quick_input_window, daemon=True).start()

    def _quick_input_window(self) -> None:
        """Minimalistické Tkinter okno — jako Spotlight."""
        try:
            import tkinter as tk
            import tkinter.font as tkfont

            root = tk.Tk()
            root.title("")
            root.configure(bg="#070b12")
            root.attributes("-topmost", True)
            root.overrideredirect(True)  # bez title baru

            # Centruj na obrazovce
            w, h = 500, 60
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            x = (sw - w) // 2
            y = sh // 3  # horní třetina obrazovky
            root.geometry(f"{w}x{h}+{x}+{y}")

            # Border efekt
            root.configure(highlightbackground="#00d4ff", highlightthickness=1)

            # Input pole
            font = tkfont.Font(family="Courier New", size=14)
            entry = tk.Entry(root, bg="#0b1220", fg="#e2f0ff",
                            insertbackground="#00d4ff",
                            font=font, bd=0, highlightthickness=0)
            entry.pack(fill="both", expand=True, padx=12, pady=14)
            entry.focus_force()

            result = {"text": ""}

            def on_enter(event=None):
                result["text"] = entry.get().strip()
                root.destroy()

            def on_escape(event=None):
                root.destroy()

            entry.bind("<Return>", on_enter)
            entry.bind("<Escape>", on_escape)
            root.bind("<FocusOut>", on_escape)  # zavři při ztrátě focusu

            root.mainloop()

            if result["text"]:
                self._callback(result["text"])
        except Exception as e:
            logger.warning(f"QuickInput okno selhalo: {e}")


_hotkey_instance: Optional[GlobalHotkey] = None


def start_global_hotkey(callback: Callable[[str], None],
                        hotkey: str = GlobalHotkey.DEFAULT_HOTKEY) -> GlobalHotkey:
    """Spustí global hotkey singleton. Bezpečně selže pokud pynput chybí."""
    global _hotkey_instance
    if _hotkey_instance is None:
        _hotkey_instance = GlobalHotkey(callback, hotkey)
    _hotkey_instance.start()
    return _hotkey_instance


def stop_global_hotkey() -> None:
    global _hotkey_instance
    if _hotkey_instance:
        _hotkey_instance.stop()
        _hotkey_instance = None
