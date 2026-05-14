"""
SettingsDialog — otevírá se přes tlačítko ⚙ v levém panelu.
"""

import customtkinter as ctk

from gui.constants import BG, BG3, BORDER, CYAN, CYAN2, FG, FG2


def open_settings(self):
    """Otevře Settings dialog."""
    dialog = ctk.CTkToplevel(self.root)
    dialog.title("NASTAVENÍ")
    dialog.geometry("400x400")
    dialog.resizable(False, False)
    dialog.configure(fg_color=BG)
    dialog.grab_set()

    self.root.update_idletasks()
    x = self.root.winfo_x() + (self.W - 400) // 2
    y = self.root.winfo_y() + (self.H - 400) // 2
    dialog.geometry(f"+{x}+{y}")

    scroll = ctk.CTkScrollableFrame(dialog, fg_color=BG, corner_radius=0)
    scroll.pack(fill="both", expand=True, padx=0, pady=0)

    # ── JAZYK STT ────────────────────────────────────
    ctk.CTkLabel(scroll, text="Jazyk rozpoznávání (STT):",
                 font=("Courier New", 11), text_color=FG).pack(anchor="w", padx=12, pady=(12, 4))

    self._lang_var = ctk.StringVar(value="cs-CZ")
    lang_opt = ctk.CTkOptionMenu(
        scroll,
        variable=self._lang_var,
        values=["cs-CZ", "en-US", "en-GB", "es-ES", "fr-FR", "de-DE", "it-IT", "pt-BR", "pl-PL", "ru-RU"],
        command=self._on_language_select,
        fg_color=BG3, button_color=CYAN2,
        button_hover_color=BORDER,
        text_color=FG, dropdown_text_color=FG,
        font=("DM Sans", 11),
        corner_radius=4,
    )
    lang_opt.pack(anchor="w", padx=12, pady=(0, 12), fill="x")

    ctk.CTkLabel(scroll, text="",
                 font=("Courier New", 8), text_color=BORDER).pack()

    # ── ENERGETICKÝ PRÁH ─────────────────────────────
    ctk.CTkLabel(scroll, text="Citlivost mikrofonu (energetický práh):",
                 font=("Courier New", 11), text_color=FG).pack(anchor="w", padx=12, pady=(12, 4))

    self._energy_var = ctk.IntVar(value=300)
    energy_slider = ctk.CTkSlider(
        scroll,
        from_=100, to=4000,
        variable=self._energy_var,
        command=self._on_energy_change,
        fg_color=BORDER, progress_color=CYAN,
        button_color=CYAN2, button_hover_color=CYAN,
        corner_radius=4, height=6,
    )
    energy_slider.pack(anchor="w", padx=12, pady=(0, 6), fill="x")

    self._energy_lbl = ctk.CTkLabel(scroll, text="300",
                                     font=("Courier New", 10), text_color=FG2)
    self._energy_lbl.pack(anchor="w", padx=12, pady=(0, 12))

    ctk.CTkLabel(scroll, text="Nižší = citlivější",
                 font=("Courier New", 8), text_color=BORDER).pack(anchor="w", padx=12)

    ctk.CTkLabel(scroll, text="",
                 font=("Courier New", 8), text_color=BORDER).pack()

    # ── RYCHLOST TTS ────────────────────────────────
    ctk.CTkLabel(scroll, text="Rychlost TTS:",
                 font=("Courier New", 11), text_color=FG).pack(anchor="w", padx=12, pady=(12, 4))

    self._tts_var = ctk.IntVar(value=170)
    tts_slider = ctk.CTkSlider(
        scroll,
        from_=100, to=250,
        variable=self._tts_var,
        command=self._on_tts_change,
        fg_color=BORDER, progress_color=CYAN,
        button_color=CYAN2, button_hover_color=CYAN,
        corner_radius=4, height=6,
    )
    tts_slider.pack(anchor="w", padx=12, pady=(0, 6), fill="x")

    self._tts_lbl = ctk.CTkLabel(scroll, text="170",
                                  font=("Courier New", 10), text_color=FG2)
    self._tts_lbl.pack(anchor="w", padx=12, pady=(0, 12))

    ctk.CTkLabel(scroll, text="Vyšší = rychleji",
                 font=("Courier New", 8), text_color=BORDER).pack(anchor="w", padx=12)

    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
