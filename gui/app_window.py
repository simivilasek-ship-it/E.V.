"""
JARVIS v3.1 — hlavní okno (OpenCode styl)
Top bar → fullwidth chat → bottom input bar.
"""

from __future__ import annotations

import re
import subprocess
import tkinter as tk
from datetime import datetime
from typing import Optional

import customtkinter as ctk

from gui.constants import (
    BG, BG2, BG3, FG, FG2, BORDER,
    CYAN, CYAN2, GREEN, RED, PURPLE,
    ORB_COLORS, STATE_LABELS,
    blend, lerp,
)
from gui.orb import OrbCanvas, MiniOrbCanvas

FONT_MONO   = ("Courier New", 11)
FONT_MONO_S = ("Courier New", 9)
FONT_UI     = ("DM Sans", 12)
FONT_UI_S   = ("DM Sans", 10)

STATE_COLOR = {
    "idle":      FG2,
    "listening": GREEN,
    "thinking":  PURPLE,
    "speaking":  CYAN,
}
STATE_ICON = {
    "idle":      "○",
    "listening": "◉",
    "thinking":  "◎",
    "speaking":  "●",
}


class JarvisGUI:
    """
    OpenCode-style layout 1100×700:

    ┌─────────────────────────────────────────────────────┐
    │  ⬡ orb  JARVIS  ○ idle    model ▾  🔊62%  14:32  ⚙│  top bar
    ├─────────────────────────────────────────────────────┤
    │                                                     │
    │   ┌─ jarvis ─────────────────────────────────────┐  │
    │   │  Ahoj! Jak ti mohu pomoct?                   │  │
    │   └──────────────────────────────────────────────┘  │  chat
    │                                                     │
    │             ┌──────────────────────── ty ────────┐  │
    │             │  Otevři Spotify                    │  │
    │             └────────────────────────────────────┘  │
    ├─────────────────────────────────────────────────────┤
    │  [🎤 Space]  │  Napiš zprávu...       🗑 💾 🧠 [↵] │  input bar
    └─────────────────────────────────────────────────────┘

    Veřejné API (nezměněno):
      set_state(state), add_message(text, sender), set_status(text)
      on_mic_click, on_send, on_model_change,
      on_language_change, on_energy_threshold_change, on_tts_rate_change
    """

    W, H = 1100, 700

    def __init__(self):
        self.on_mic_click:               Optional[callable] = None
        self.on_send:                    Optional[callable] = None
        self.on_model_change:            Optional[callable] = None
        self.on_language_change:         Optional[callable] = None
        self.on_energy_threshold_change: Optional[callable] = None
        self.on_tts_rate_change:         Optional[callable] = None

        self._state = "idle"
        self._setup()
        self._build()

    # ── OKNO ────────────────────────────────────────────

    def _setup(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.root = ctk.CTk()
        self.root.title("JARVIS")
        self.root.geometry(f"{self.W}x{self.H}")
        self.root.resizable(True, True)
        self.root.minsize(800, 500)
        self.root.configure(fg_color=BG)
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{self.W}x{self.H}+{(sw-self.W)//2}+{(sh-self.H)//2}")
        self.root.bind("<Return>",    self._on_enter)
        self.root.bind("<space>",     self._on_space)
        self.root.bind("<Control-l>", lambda e: self._clear_chat())
        self.root.bind("<Control-e>", lambda e: self._export_chat())
        self.root.bind("<Escape>",    lambda e: self._input.focus())

    # ── LAYOUT ──────────────────────────────────────────

    def _build(self):
        self._build_topbar()
        self._divider()
        self._build_chat()
        self._divider()
        self._build_inputbar()

    def _divider(self):
        ctk.CTkFrame(self.root, fg_color=BORDER, height=1,
                     corner_radius=0).pack(fill="x", side="top")

    # ── TOP BAR ─────────────────────────────────────────

    def _build_topbar(self):
        bar = ctk.CTkFrame(self.root, fg_color=BG2, corner_radius=0, height=54)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        # Levá strana: mini orb + název + stav
        left = ctk.CTkFrame(bar, fg_color=BG2, corner_radius=0)
        left.pack(side="left", fill="y", padx=(12, 0))

        self.orb = MiniOrbCanvas(left)
        self.orb.pack(side="left", padx=(0, 10), pady=3)

        id_col = ctk.CTkFrame(left, fg_color=BG2, corner_radius=0)
        id_col.pack(side="left", fill="y", pady=8)

        ctk.CTkLabel(
            id_col, text="JARVIS",
            font=("Courier New", 13, "bold"), text_color=CYAN,
        ).pack(anchor="w")

        self._state_lbl = ctk.CTkLabel(
            id_col, text="○  idle",
            font=FONT_MONO_S, text_color=FG2,
        )
        self._state_lbl.pack(anchor="w")

        # Pravá strana: model + čas + hlasitost + ⚙
        right = ctk.CTkFrame(bar, fg_color=BG2, corner_radius=0)
        right.pack(side="right", fill="y", padx=(0, 12))

        ctk.CTkButton(
            right, text="⚙",
            font=("DM Sans", 14),
            fg_color="transparent", hover_color=BG3,
            text_color=FG2,
            corner_radius=6, width=30, height=30,
            command=self._open_settings,
        ).pack(side="right", padx=(4, 0), pady=12)

        self._vol_lbl = ctk.CTkLabel(right, text="🔊 —",
                                      font=FONT_MONO_S, text_color=FG2)
        self._vol_lbl.pack(side="right", padx=8, pady=12)

        self._clock = ctk.CTkLabel(right, text="",
                                    font=FONT_MONO_S, text_color=FG2)
        self._clock.pack(side="right", padx=(0, 2), pady=12)

        ctk.CTkFrame(right, fg_color=BORDER, width=1, height=26,
                     corner_radius=0).pack(side="right", padx=8, pady=14)

        self._model_var = ctk.StringVar(value="qwen2.5:3b")
        self._model_opt = ctk.CTkOptionMenu(
            right,
            variable=self._model_var,
            values=["qwen2.5:3b", "llama3.1:8b", "llama3.2:3b",
                    "mistral:7b", "deepseek-coder:latest"],
            command=self._on_model_select,
            fg_color=BG3, button_color=BG3,
            button_hover_color=BORDER,
            text_color=FG, dropdown_text_color=FG,
            dropdown_fg_color=BG2,
            font=FONT_MONO_S,
            width=155, height=28,
            corner_radius=4,
        )
        self._model_opt.pack(side="right", padx=4, pady=13)

        ctk.CTkLabel(right, text="model",
                     font=FONT_MONO_S, text_color=FG2).pack(side="right", pady=12)

        self._tick_clock()
        self._refresh_vol()

    # ── CHAT ────────────────────────────────────────────

    def _build_chat(self):
        self._chat = ctk.CTkScrollableFrame(
            self.root, fg_color=BG, corner_radius=0)
        self._chat.pack(fill="both", expand=True, side="top")
        self._add_sys("JARVIS v3.1 připraven.  Ctrl+L = clear  Ctrl+E = export  Space = mic")

    # ── INPUT BAR ───────────────────────────────────────

    def _build_inputbar(self):
        bar = ctk.CTkFrame(self.root, fg_color=BG2, corner_radius=0, height=56)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        # Mic
        self.mic_btn = ctk.CTkButton(
            bar, text="🎤  Space",
            font=FONT_MONO_S,
            fg_color=BG3, hover_color=BORDER,
            text_color=CYAN,
            corner_radius=6, width=96, height=34,
            command=self._on_mic,
        )
        self.mic_btn.pack(side="left", padx=(12, 0), pady=11)

        ctk.CTkFrame(bar, fg_color=BORDER, width=1, height=28,
                     corner_radius=0).pack(side="left", padx=10, pady=14)

        # Akční ikony před send
        for txt, cmd in [("🗑", self._clear_chat),
                         ("💾", self._export_chat),
                         ("🧠", self._clear_mem)]:
            ctk.CTkButton(
                bar, text=txt,
                font=("DM Sans", 13),
                fg_color="transparent", hover_color=BG3,
                text_color=FG2,
                corner_radius=4, width=28, height=28,
                command=cmd,
            ).pack(side="right", padx=2, pady=14)

        # Send
        ctk.CTkButton(
            bar, text="↵",
            font=("Courier New", 16),
            fg_color=CYAN2, hover_color=CYAN,
            text_color=BG,
            corner_radius=6, width=42, height=34,
            command=self._send,
        ).pack(side="right", padx=(0, 12), pady=11)

        ctk.CTkFrame(bar, fg_color=BORDER, width=1, height=28,
                     corner_radius=0).pack(side="right", padx=6, pady=14)

        # Input pole
        self._input = ctk.CTkEntry(
            bar,
            placeholder_text="Napiš zprávu nebo příkaz...",
            font=FONT_UI,
            fg_color=BG3, text_color=FG,
            placeholder_text_color=FG2,
            border_color=BORDER, border_width=1,
            corner_radius=6, height=34,
        )
        self._input.pack(side="left", fill="x", expand=True, pady=11)
        self._input.bind("<Return>", self._on_enter)
        self._input.focus()

    # ── CHAT HELPERS ────────────────────────────────────

    def _add_sys(self, text: str):
        f = ctk.CTkFrame(self._chat, fg_color="transparent", corner_radius=0)
        f.pack(fill="x", padx=24, pady=(8, 2))
        ctk.CTkLabel(f, text=text, font=FONT_MONO_S, text_color=FG2).pack(anchor="w")

    def add_message(self, text: str, sender: str):
        import gui.chat as _chat_mod
        _chat_mod.add_message(self, text, sender)

    def _render_message(self, parent, text: str, is_user: bool):
        import gui.chat as _chat_mod
        _chat_mod._render_message(self, parent, text, is_user)

    def _export_chat(self):
        import gui.chat as _chat_mod
        _chat_mod.export_chat(self)

    # ── HODINY + HLASITOST ──────────────────────────────

    def _tick_clock(self):
        self._clock.configure(text=datetime.now().strftime("%H:%M:%S"))
        self.root.after(1000, self._tick_clock)

    def _refresh_vol(self):
        try:
            result = subprocess.run(
                ["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                capture_output=True, text=True, timeout=1,
            )
            if result.returncode == 0:
                m = re.search(r"(\d+)%", result.stdout)
                if m:
                    pct = int(m.group(1))
                    icon = "🔊" if pct > 50 else ("🔉" if pct > 0 else "🔇")
                    col  = RED if pct > 90 else (CYAN if pct > 50 else FG2)
                    self._vol_lbl.configure(text=f"{icon} {pct}%", text_color=col)
        except Exception:
            pass
        self.root.after(3000, self._refresh_vol)

    # ── VEŘEJNÉ API ─────────────────────────────────────

    def set_state(self, state: str):
        if state not in ORB_COLORS:
            return
        self._state = state
        self.orb.set_state(state)
        speeds = {"idle": 0.5, "listening": 2.2, "thinking": 1.5, "speaking": 1.9}
        self.orb.set_speed(speeds.get(state, 1.0))

        icon = STATE_ICON.get(state, "○")
        col  = STATE_COLOR.get(state, FG2)
        self._state_lbl.configure(text=f"{icon}  {state}", text_color=col)

        mic_map = {
            "idle":      ("🎤  Space", CYAN),
            "listening": ("◉  Space",  GREEN),
            "thinking":  ("◎  ...",    PURPLE),
            "speaking":  ("●  Space",  CYAN),
        }
        txt, tc = mic_map.get(state, ("🎤  Space", CYAN))
        self.mic_btn.configure(text=txt, text_color=tc)

    def set_status(self, text: str):
        self._add_sys(text)

    def run(self):
        self.root.mainloop()

    def update_model_list(self, models: list, current: str = ""):
        if models:
            self._model_opt.configure(values=models)
        if current:
            self._model_var.set(current)

    # ── INTERNÍ ─────────────────────────────────────────

    def _open_settings(self):
        import gui.settings as _settings_mod
        _settings_mod.open_settings(self)

    def _on_mic(self):
        if self.on_mic_click:
            self.on_mic_click()

    def _on_space(self, event):
        if not isinstance(self.root.focus_get(), (tk.Entry, ctk.CTkEntry)):
            self._on_mic()

    def _on_enter(self, event=None):
        self._send()

    def _send(self):
        text = self._input.get().strip()
        if not text:
            return
        self._input.delete(0, "end")
        if self.on_send:
            self.on_send(text)
        else:
            self.add_message(text, "user")

    def _on_model_select(self, value: str):
        if self.on_model_change:
            self.on_model_change(value)
        self._add_sys(f"Model: {value}")

    def _on_language_select(self, value: str):
        if self.on_language_change:
            self.on_language_change(value)
        self._add_sys(f"Jazyk STT: {value}")

    def _on_energy_change(self, value):
        val = int(float(value))
        self._energy_lbl.configure(text=str(val))
        if self.on_energy_threshold_change:
            self.on_energy_threshold_change(val)

    def _on_tts_change(self, value):
        val = int(float(value))
        self._tts_lbl.configure(text=str(val))
        if self.on_tts_rate_change:
            self.on_tts_rate_change(val)

    def _clear_chat(self):
        for w in self._chat.winfo_children():
            w.destroy()
        self._add_sys("Log vymazán.")

    def _clear_mem(self):
        self._add_sys("Paměť vymazána.")
