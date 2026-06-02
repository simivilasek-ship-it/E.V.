"""
SettingsDialog — otevírá se přes tlačítko ⚙ v top baru.
"""

import customtkinter as ctk
from config import CONFIG, save_config
from gui.constants import BG, BG3, BORDER, CYAN, CYAN2, FG, FG2

FONT_LABEL = ("DM Sans", 12)
FONT_SECTION = ("DM Sans", 13, "bold")
FONT_SMALL = ("DM Sans", 10)


def _section(parent, title: str):
    ctk.CTkLabel(parent, text=title, font=FONT_SECTION, text_color=CYAN).pack(
        anchor="w", padx=16, pady=(18, 4)
    )
    ctk.CTkFrame(parent, height=1, fg_color=BORDER, corner_radius=0).pack(
        fill="x", padx=16, pady=(0, 8)
    )


def _row(parent):
    f = ctk.CTkFrame(parent, fg_color="transparent")
    f.pack(fill="x", padx=16, pady=3)
    return f


def open_settings(self):
    dialog = ctk.CTkToplevel(self.root)
    dialog.title("Nastavení JARVIS")
    dialog.geometry("480x620")
    dialog.resizable(False, False)
    dialog.configure(fg_color=BG)
    dialog.grab_set()

    self.root.update_idletasks()
    x = self.root.winfo_x() + (self.W - 480) // 2
    y = self.root.winfo_y() + (self.H - 620) // 2
    dialog.geometry(f"+{x}+{y}")

    scroll = ctk.CTkScrollableFrame(dialog, fg_color=BG, corner_radius=0)
    scroll.pack(fill="both", expand=True, padx=0, pady=0)

    # ── LLM ─────────────────────────────────────────────
    _section(scroll, "Model")

    r = _row(scroll)
    ctk.CTkLabel(r, text="Ollama URL:", font=FONT_LABEL, text_color=FG, width=160, anchor="w").pack(side="left")
    url_var = ctk.StringVar(value=CONFIG.get("ollama_url", "http://localhost:11434/api/chat"))
    ctk.CTkEntry(r, textvariable=url_var, font=FONT_SMALL, fg_color=BG3,
                 text_color=FG, border_color=BORDER, border_width=1, corner_radius=4, height=28).pack(side="left", fill="x", expand=True)

    r = _row(scroll)
    ctk.CTkLabel(r, text="Historie zpráv:", font=FONT_LABEL, text_color=FG, width=160, anchor="w").pack(side="left")
    hist_var = ctk.StringVar(value=str(CONFIG.get("history_size", 20)))
    ctk.CTkEntry(r, textvariable=hist_var, font=FONT_SMALL, fg_color=BG3,
                 text_color=FG, border_color=BORDER, border_width=1, corner_radius=4, height=28, width=60).pack(side="left")

    # ── STT ─────────────────────────────────────────────
    _section(scroll, "Rozpoznávání hlasu (STT)")

    r = _row(scroll)
    ctk.CTkLabel(r, text="Jazyk:", font=FONT_LABEL, text_color=FG, width=160, anchor="w").pack(side="left")
    self._lang_var = ctk.StringVar(value=CONFIG.get("stt_language", "cs-CZ"))
    ctk.CTkOptionMenu(
        r, variable=self._lang_var,
        values=["cs-CZ", "en-US", "en-GB", "es-ES", "fr-FR", "de-DE", "it-IT", "pt-BR", "pl-PL", "ru-RU"],
        command=self._on_language_select,
        fg_color=BG3, button_color=CYAN2, button_hover_color=BORDER,
        text_color=FG, dropdown_text_color=FG, font=FONT_SMALL, corner_radius=4,
    ).pack(side="left", fill="x", expand=True)

    r = _row(scroll)
    ctk.CTkLabel(r, text="Citlivost mikrofonu:", font=FONT_LABEL, text_color=FG, width=160, anchor="w").pack(side="left")
    self._energy_var = ctk.IntVar(value=CONFIG.get("stt_energy_threshold", 300))
    ctk.CTkSlider(r, from_=100, to=4000, variable=self._energy_var, command=self._on_energy_change,
                  fg_color=BORDER, progress_color=CYAN, button_color=CYAN2,
                  button_hover_color=CYAN, corner_radius=4, height=6).pack(side="left", fill="x", expand=True, padx=(0, 8))
    self._energy_lbl = ctk.CTkLabel(r, text=str(self._energy_var.get()), font=FONT_SMALL, text_color=FG2, width=40)
    self._energy_lbl.pack(side="left")

    # ── TTS ─────────────────────────────────────────────
    _section(scroll, "Syntéza hlasu (TTS)")

    r = _row(scroll)
    tts_enabled_var = ctk.BooleanVar(value=CONFIG.get("tts_enabled", True))
    ctk.CTkLabel(r, text="TTS zapnuto:", font=FONT_LABEL, text_color=FG, width=160, anchor="w").pack(side="left")
    ctk.CTkSwitch(r, variable=tts_enabled_var, text="", fg_color=BORDER,
                  progress_color=CYAN, button_color=CYAN2).pack(side="left")

    r = _row(scroll)
    ctk.CTkLabel(r, text="Hlas:", font=FONT_LABEL, text_color=FG, width=160, anchor="w").pack(side="left")
    voice_var = ctk.StringVar(value=CONFIG.get("tts_voice", "cs-CZ-AntoninNeural"))
    ctk.CTkOptionMenu(
        r, variable=voice_var,
        values=["cs-CZ-AntoninNeural", "cs-CZ-VlastaNeural", "en-US-AriaNeural", "en-US-GuyNeural",
                "de-DE-KatjaNeural", "fr-FR-DeniseNeural"],
        fg_color=BG3, button_color=CYAN2, button_hover_color=BORDER,
        text_color=FG, dropdown_text_color=FG, font=FONT_SMALL, corner_radius=4,
    ).pack(side="left", fill="x", expand=True)

    r = _row(scroll)
    ctk.CTkLabel(r, text="Rychlost TTS:", font=FONT_LABEL, text_color=FG, width=160, anchor="w").pack(side="left")
    self._tts_var = ctk.IntVar(value=CONFIG.get("tts_rate", 170))
    ctk.CTkSlider(r, from_=100, to=250, variable=self._tts_var, command=self._on_tts_change,
                  fg_color=BORDER, progress_color=CYAN, button_color=CYAN2,
                  button_hover_color=CYAN, corner_radius=4, height=6).pack(side="left", fill="x", expand=True, padx=(0, 8))
    self._tts_lbl = ctk.CTkLabel(r, text=str(self._tts_var.get()), font=FONT_SMALL, text_color=FG2, width=40)
    self._tts_lbl.pack(side="left")

    # ── MCP ─────────────────────────────────────────────
    _section(scroll, "MCP servery")

    mcp_items = [
        ("Filesystem",  "mcp_filesystem_enabled"),
        ("Git",         "mcp_git_enabled"),
        ("Memory",      "mcp_memory_enabled"),
        ("Brave Search","mcp_brave_enabled"),
        ("Fetch",       "mcp_fetch_enabled"),
        ("Playwright",  "mcp_playwright_enabled"),
    ]
    mcp_vars: dict[str, ctk.BooleanVar] = {}
    for label, key in mcp_items:
        r = _row(scroll)
        var = ctk.BooleanVar(value=CONFIG.get(key, False))
        mcp_vars[key] = var
        ctk.CTkLabel(r, text=label + ":", font=FONT_LABEL, text_color=FG, width=160, anchor="w").pack(side="left")
        ctk.CTkSwitch(r, variable=var, text="", fg_color=BORDER,
                      progress_color=CYAN, button_color=CYAN2).pack(side="left")

    # ── LOGY ────────────────────────────────────────────
    _section(scroll, "Logy")

    r = _row(scroll)
    ctk.CTkLabel(r, text="Úroveň logů:", font=FONT_LABEL, text_color=FG, width=160, anchor="w").pack(side="left")
    log_var = ctk.StringVar(value=CONFIG.get("log_level", "INFO"))
    ctk.CTkOptionMenu(
        r, variable=log_var,
        values=["DEBUG", "INFO", "WARNING", "ERROR"],
        fg_color=BG3, button_color=CYAN2, button_hover_color=BORDER,
        text_color=FG, dropdown_text_color=FG, font=FONT_SMALL, corner_radius=4,
    ).pack(side="left", fill="x", expand=True)

    r = _row(scroll)
    audit_var = ctk.BooleanVar(value=CONFIG.get("audit_enabled", True))
    ctk.CTkLabel(r, text="Audit log:", font=FONT_LABEL, text_color=FG, width=160, anchor="w").pack(side="left")
    ctk.CTkSwitch(r, variable=audit_var, text="", fg_color=BORDER,
                  progress_color=CYAN, button_color=CYAN2).pack(side="left")

    # ── ULOŽIT ──────────────────────────────────────────
    def _save():
        try:
            CONFIG["ollama_url"] = url_var.get().strip()
            CONFIG["history_size"] = max(1, int(hist_var.get()))
            CONFIG["tts_enabled"] = tts_enabled_var.get()
            CONFIG["tts_voice"] = voice_var.get()
            CONFIG["tts_rate"] = self._tts_var.get()
            CONFIG["stt_language"] = self._lang_var.get()
            CONFIG["stt_energy_threshold"] = self._energy_var.get()
            CONFIG["log_level"] = log_var.get()
            CONFIG["audit_enabled"] = audit_var.get()
            for key, var in mcp_vars.items():
                CONFIG[key] = var.get()
            save_config(CONFIG)
            self._add_sys("Nastavení uloženo.")
            dialog.destroy()
        except Exception as e:
            self._add_sys(f"Chyba při ukládání: {e}")

    ctk.CTkButton(
        scroll, text="Uložit nastavení",
        command=_save,
        fg_color=CYAN2, hover_color=CYAN, text_color="#000000",
        font=("DM Sans", 12, "bold"), corner_radius=6, height=36,
    ).pack(fill="x", padx=16, pady=(16, 20))

    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
