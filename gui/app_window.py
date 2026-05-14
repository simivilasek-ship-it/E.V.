"""
JARVIS v3.0 — hlavní okno JarvisGUI.
"""

import tkinter as tk
import customtkinter as ctk
from datetime import datetime

from gui.constants import (
    BG, BG2, BG3, FG, FG2, BORDER,
    CYAN, CYAN2, GREEN, RED, PURPLE,
    ORB_COLORS, STATE_LABELS,
    blend, lerp,
)
from gui.orb import OrbCanvas
import gui.chat as _chat_mod
import gui.settings as _settings_mod


class JarvisGUI:
    """
    Rozdělený layout 820×560:
    ┌─────────────────┬──────────────────────────┐
    │  ORB + STAV     │  CHAT LOG                │
    │  ovládání       │  zprávy                  │
    │                 │  input                   │
    └─────────────────┴──────────────────────────┘

    Veřejné API:
      set_state(state)          — idle|listening|thinking|speaking
      add_message(text, sender) — user|jarvis
      set_status(text)          — info pod orbem
      on_mic_click, on_send, on_model_change,
      on_language_change, on_energy_threshold_change,
      on_tts_rate_change        — callbacky
    """

    W, H = 820, 560
    LEFT_W = 300

    def __init__(self):
        self.on_mic_click:              callable = None
        self.on_send:                   callable = None
        self.on_model_change:           callable = None
        self.on_language_change:        callable = None
        self.on_energy_threshold_change: callable = None
        self.on_tts_rate_change:        callable = None

        self._state = "idle"
        self._setup()
        self._build()

    # ── OKNO ─────────────────────────────────────────

    def _setup(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.root = ctk.CTk()
        self.root.title("JARVIS")
        self.root.geometry(f"{self.W}x{self.H}")
        self.root.resizable(False, False)
        self.root.configure(fg_color=BG)
        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{self.W}x{self.H}+{(sw-self.W)//2}+{(sh-self.H)//2}")
        self.root.bind("<Return>",    self._on_enter)
        self.root.bind("<space>",     self._on_space)
        self.root.bind("<Control-l>", lambda e: self._clear_chat())
        self.root.bind("<Control-e>", lambda e: self._export_chat())
        self.root.bind("<Escape>",    lambda e: self._input.focus())

    # ── LAYOUT ───────────────────────────────────────

    def _build(self):
        left  = ctk.CTkFrame(self.root, fg_color=BG2,
                              width=self.LEFT_W, height=self.H, corner_radius=0)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        right = ctk.CTkFrame(self.root, fg_color=BG, corner_radius=0)
        right.pack(side="left", fill="both", expand=True)

        ctk.CTkFrame(self.root, fg_color=BORDER, width=1,
                     corner_radius=0, height=self.H).place(x=self.LEFT_W, y=0)

        self._build_left(left)
        self._build_right(right)

    # ── LEVÝ PANEL ────────────────────────────────────

    def _build_left(self, parent):
        hdr = ctk.CTkFrame(parent, fg_color=BG, corner_radius=0, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="J A R V I S",
                     font=("Courier New", 15), text_color=CYAN).pack(
            side="left", padx=16, pady=12)

        self._status_dot = ctk.CTkLabel(hdr, text="●", font=("DM Sans", 10),
                                         text_color=BORDER)
        self._status_dot.pack(side="right", padx=14)

        ctk.CTkFrame(parent, fg_color=BORDER, height=1, corner_radius=0).pack(fill="x")

        orb_frame = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=0)
        orb_frame.pack(fill="x", pady=(18, 0))

        self.orb = OrbCanvas(orb_frame)
        self.orb.pack(anchor="center")

        self._state_lbl = ctk.CTkLabel(
            orb_frame, text="● IDLE",
            font=("Courier New", 10), text_color=ORB_COLORS["idle"])
        self._state_lbl.pack(pady=(6, 2))

        self._info_lbl = ctk.CTkLabel(
            orb_frame, text="",
            font=("DM Sans", 10), text_color=FG2)
        self._info_lbl.pack(pady=(0, 8))

        bottom_row = ctk.CTkFrame(orb_frame, fg_color=BG2, corner_radius=0)
        bottom_row.pack(fill="x", padx=8)

        self._clock = ctk.CTkLabel(
            bottom_row, text="",
            font=("Courier New", 9), text_color=BORDER)
        self._clock.pack(side="left", padx=(4, 0))

        self._vol_lbl = ctk.CTkLabel(
            bottom_row, text="🔊 —",
            font=("Courier New", 9), text_color=BORDER)
        self._vol_lbl.pack(side="right", padx=(0, 4))

        self._tick_clock()
        self._refresh_vol()

        ctk.CTkFrame(parent, fg_color=BORDER, height=1, corner_radius=0).pack(fill="x", pady=(12, 0))

        self._build_model_bar(parent)
        self._build_settings_bar(parent)

        ctk.CTkFrame(parent, fg_color=BORDER, height=1, corner_radius=0).pack(fill="x", pady=(0, 0))

        self._build_mic_area(parent)

    def _build_model_bar(self, parent):
        bar = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=0, height=40)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(bar, text="MODEL", font=("Courier New", 8),
                     text_color=BORDER).pack(side="left", padx=10)

        self._model_var = ctk.StringVar(value="qwen2.5:3b")
        self._model_opt = ctk.CTkOptionMenu(
            bar,
            variable=self._model_var,
            values=["qwen2.5:3b", "llama3.1:8b", "llama3.2:3b",
                    "mistral:7b", "deepseek-coder:latest"],
            command=self._on_model_select,
            fg_color=BG3, button_color=CYAN2,
            button_hover_color=BORDER,
            text_color=FG, dropdown_text_color=FG,
            font=("DM Sans", 11),
            width=170, height=28,
            corner_radius=4,
        )
        self._model_opt.pack(side="left", padx=6)

    def _build_settings_bar(self, parent):
        bar = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=0, height=40)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(bar, text="NASTAVENÍ", font=("Courier New", 8),
                     text_color=BORDER).pack(side="left", padx=10)

        ctk.CTkButton(
            bar, text="⚙",
            font=("DM Sans", 16),
            fg_color=BG3, hover_color=BORDER,
            text_color=CYAN,
            corner_radius=4, width=36, height=28,
            command=self._open_settings
        ).pack(side="left", padx=6)

    def _build_mic_area(self, parent):
        area = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=0)
        area.pack(fill="both", expand=True)

        mic_wrap = ctk.CTkFrame(area, fg_color=BG2, corner_radius=0)
        mic_wrap.place(relx=0.5, rely=0.38, anchor="center")

        ring = ctk.CTkFrame(mic_wrap, fg_color=BG2,
                            border_color=CYAN, border_width=2,
                            corner_radius=50, width=72, height=72)
        ring.pack()
        ring.pack_propagate(False)

        self.mic_btn = ctk.CTkButton(
            ring, text="🎤",
            font=("DM Sans", 24),
            fg_color=BG3, hover_color=BORDER,
            text_color=CYAN,
            corner_radius=50, width=64, height=64,
            command=self._on_mic)
        self.mic_btn.place(relx=0.5, rely=0.5, anchor="center")

        self._mic_lbl = ctk.CTkLabel(
            mic_wrap, text="Klikni nebo mezerník",
            font=("Courier New", 9), text_color=FG2)
        self._mic_lbl.pack(pady=(6, 0))

        btn_row = ctk.CTkFrame(area, fg_color=BG2, corner_radius=0)
        btn_row.place(relx=0.5, rely=0.72, anchor="center")

        for txt, cmd, tip in [
            ("🗑", self._clear_chat, "Vymazat chat (Ctrl+L)"),
            ("💾", self._export_chat, "Exportovat chat (Ctrl+E)"),
            ("🧠", self._clear_mem,  "Vymazat paměť LLM"),
        ]:
            b = ctk.CTkButton(btn_row, text=txt,
                              font=("DM Sans", 14), fg_color=BG3,
                              hover_color=BORDER, text_color=FG2,
                              corner_radius=8, width=36, height=36,
                              command=cmd)
            b.pack(side="left", padx=4)

    # ── PRAVÝ PANEL (CHAT) ────────────────────────────

    def _build_right(self, parent):
        hdr = ctk.CTkFrame(parent, fg_color=BG, corner_radius=0, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="KOMUNIKACE",
                     font=("Courier New", 10), text_color=BORDER).pack(
            side="left", padx=16, pady=14)

        ctk.CTkFrame(parent, fg_color=BORDER, height=1, corner_radius=0).pack(fill="x")

        self._chat = ctk.CTkScrollableFrame(
            parent, fg_color=BG, corner_radius=0)
        self._chat.pack(fill="both", expand=True, padx=0, pady=0)

        ctk.CTkFrame(parent, fg_color=BORDER, height=1, corner_radius=0).pack(fill="x")

        inp = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=0, height=56)
        inp.pack(fill="x")
        inp.pack_propagate(False)

        self._input = ctk.CTkEntry(
            inp,
            placeholder_text="Napiš příkaz pro JARVIS...",
            font=("DM Sans", 13),
            fg_color=BG3, text_color=FG,
            border_color=BORDER, border_width=1,
            corner_radius=8, height=36,
        )
        self._input.place(x=12, rely=0.5, anchor="w", relwidth=0.84)
        self._input.bind("<Return>", self._on_enter)
        self._input.focus()

        ctk.CTkButton(
            inp, text="↵",
            font=("Georgia", 18),
            fg_color=CYAN2, hover_color=BORDER,
            text_color=FG, corner_radius=8,
            width=42, height=36,
            command=self._send,
        ).place(relx=0.97, rely=0.5, anchor="e")

        self._add_sys("JARVIS v3.0 připraven.")

    # ── CHAT HELPERS ─────────────────────────────────

    def _add_sys(self, text):
        f = ctk.CTkFrame(self._chat, fg_color="transparent", corner_radius=0)
        f.pack(fill="x", pady=2)
        ctk.CTkLabel(f, text=text, font=("Courier New", 9),
                     text_color=BORDER).pack(anchor="center")

    # Delegace na gui.chat
    def add_message(self, text: str, sender: str):
        _chat_mod.add_message(self, text, sender)

    def _render_message(self, parent, text: str, is_user: bool):
        _chat_mod._render_message(self, parent, text, is_user)

    def _export_chat(self):
        _chat_mod.export_chat(self)

    # ── HODINY ───────────────────────────────────────

    def _tick_clock(self):
        self._clock.configure(text=datetime.now().strftime("%H:%M:%S"))
        self.root.after(1000, self._tick_clock)

    def _refresh_vol(self):
        """Přečte aktuální hlasitost a zobrazí v GUI. Opakuje se každých 3s."""
        try:
            import subprocess, re
            result = subprocess.run(
                ["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                capture_output=True, text=True, timeout=1,
            )
            if result.returncode == 0:
                m = re.search(r"(\d+)%", result.stdout)
                if m:
                    pct = int(m.group(1))
                    icon = "🔊" if pct > 50 else ("🔉" if pct > 0 else "🔇")
                    self._vol_lbl.configure(text=f"{icon} {pct}%",
                                            text_color=CYAN if pct > 80 else BORDER)
        except Exception:
            pass
        self.root.after(3000, self._refresh_vol)

    # ── VEŘEJNÉ API ──────────────────────────────────

    def set_state(self, state: str):
        if state not in ORB_COLORS:
            return
        self._state = state
        self.orb.set_state(state)
        self._state_lbl.configure(
            text=STATE_LABELS.get(state, state.upper()),
            text_color=ORB_COLORS[state])
        mic_texts = {
            "idle":      "Klikni nebo mezerník",
            "listening": "● Poslouchám...",
            "thinking":  "● Zpracovávám...",
            "speaking":  "● Mluvím...",
        }
        self._mic_lbl.configure(
            text=mic_texts.get(state, ""),
            text_color=ORB_COLORS.get(state, FG2))
        self.mic_btn.configure(text_color=ORB_COLORS.get(state, CYAN))
        dot_colors = {"idle": BORDER, "listening": RED,
                      "thinking": PURPLE, "speaking": GREEN}
        self._status_dot.configure(
            text_color=dot_colors.get(state, BORDER))

    def set_status(self, text: str):
        self._info_lbl.configure(text=text)

    def run(self):
        self.root.mainloop()

    # ── INTERNÍ ──────────────────────────────────────

    def _open_settings(self):
        _settings_mod.open_settings(self)

    def _on_language_select(self, value):
        if self.on_language_change:
            self.on_language_change(value)
        self._add_sys(f"Jazyk: {value}")

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

    def _clear_chat(self):
        for w in self._chat.winfo_children():
            w.destroy()
        self._add_sys("Log vymazán.")

    def _clear_mem(self):
        self._add_sys("Paměť vymazána.")

    def _on_model_select(self, value):
        if self.on_model_change:
            self.on_model_change(value)
        self._add_sys(f"Model: {value}")

    def update_model_list(self, models: list, current: str = ""):
        """Aktualizuje dropdown s dostupnými modely z Ollama."""
        if models:
            self._model_opt.configure(values=models)
        if current:
            self._model_var.set(current)
