"""
JARVIS v2.0 — Hlasový asistent
Hlavní orchestrátor aplikace s vylepšeným GUI
"""

import logging
import sys
import signal
import threading
import re
import tkinter as tk

# Import modulů
from config import CONFIG, AVAILABLE_OLLAMA_MODELS, save_config
from stt import STTEngine
from tts import TTSEngine
from llm import LLMEngine
from commands import CommandExecutor

# GUI
import customtkinter as ctk
from datetime import datetime

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════
#  KONSTANTY A BARVY
# ══════════════════════════════════════════════════════

GOLD  = "#b06d00"
GOLDH = "#c87f10"
BG    = "#0f0d0a"
BG2   = "#1a1510"
BG3   = "#221d16"
FG    = "#f0ead8"
MUTED = "#777777"
GREEN = "#4caf50"
RED   = "#e53935"
BLUE  = "#64b5f6"

APP_VERSION = "2.0"

# Barvy ORBu pro každý stav asistenta
ORB_COLORS = {
    "idle":      GOLD,
    "listening": RED,
    "thinking":  BLUE,
    "speaking":  GREEN,
}

# ══════════════════════════════════════════════════════
#  ORB WIDGET — Animovaný indikátor stavu
# ══════════════════════════════════════════════════════

class OrbWidget:
    """
    Pulzující kruh (48×48 px) zobrazující stav asistenta.
    Animuje se každých 40 ms, poloměr kolísá mezi 12–20 px.
    Glow efekt je tvořen druhým průhledným kruhem s obrysem.
    """

    def __init__(self, parent):
        self.canvas = tk.Canvas(
            parent, width=48, height=48,
            bg=BG2, highlightthickness=0,
        )
        self.canvas.pack(side="left", padx=(14, 0), pady=10)
        self._state     = "idle"
        self._radius    = 16.0
        self._direction = 1       # 1 = roste, -1 = klesá
        self._running   = True
        self._animate()

    def set_state(self, state: str):
        """Nastaví stav → změní barvu ORBu"""
        self._state = state

    def stop(self):
        """Zastaví animační smyčku"""
        self._running = False

    def _animate(self):
        if not self._running:
            return
        self.canvas.delete("all")
        color = ORB_COLORS.get(self._state, GOLD)
        cx, cy = 24, 24

        # Glow — větší průhledný kruh s obrysem
        gr = self._radius + 5
        self.canvas.create_oval(
            cx - gr, cy - gr, cx + gr, cy + gr,
            fill="", outline=color, width=1,
        )

        # Hlavní pulzující kruh
        self.canvas.create_oval(
            cx - self._radius, cy - self._radius,
            cx + self._radius, cy + self._radius,
            fill=color, outline="",
        )

        # Pulsace
        self._radius += self._direction * 0.35
        if self._radius >= 20:
            self._direction = -1
        elif self._radius <= 12:
            self._direction = 1

        self.canvas.after(40, self._animate)


# ══════════════════════════════════════════════════════
#  HLAVNÍ APLIKACE
# ══════════════════════════════════════════════════════

class JarvisApp:
    """Hlavní aplikace JARVIS"""

    def __init__(self):
        self._setup_logging()
        logger.info("Spouštím JARVIS v2.0...")

        # Inicializuj komponenty
        try:
            self.stt      = STTEngine(CONFIG)
            self.tts      = TTSEngine(CONFIG)
            self.llm      = LLMEngine(CONFIG)
            self.commands = CommandExecutor(CONFIG)
        except Exception as e:
            logger.error(f"Chyba inicializace: {e}")
            sys.exit(1)

        # Stav aplikace
        self._is_listening   = False
        self._thinking_job   = None
        self._shutdown_event = threading.Event()
        self._dark_mode      = CONFIG.get("theme", "dark") == "dark"

        self._setup_gui()

        signal.signal(signal.SIGINT,  self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.root.after(300, self._check_ollama)
        logger.info("JARVIS připraven")

    # ── LOGGING ──────────────────────────────────────────────

    def _setup_logging(self):
        level = getattr(logging, CONFIG.get("log_level", "INFO").upper())
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("jarvis.log", encoding="utf-8"),
            ],
        )

    # ── GUI SETUP ────────────────────────────────────────────

    def _setup_gui(self):
        ctk.set_appearance_mode("dark" if self._dark_mode else "light")
        ctk.set_default_color_theme("dark-blue")

        self.root = ctk.CTk()
        self.root.title(f"JARVIS v{APP_VERSION}")
        self.root.geometry(CONFIG["window_size"])
        self.root.minsize(440, 600)
        self.root.configure(fg_color=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()

    def _build_ui(self):
        self._build_header()
        self._build_toolbar()
        self._build_model_row()
        ctk.CTkFrame(self.root, fg_color=GOLD, height=1, corner_radius=0).pack(fill="x")
        self._build_chat_log()
        self._build_progress()
        ctk.CTkFrame(self.root, fg_color=BG3, height=1, corner_radius=0).pack(fill="x")
        self._build_mic_area()
        self._build_input_row()

        self._log_system("JARVIS v2.0 spuštěn. Napiš příkaz nebo mluv.")
        self._tick_clock()

    # ── HEADER ───────────────────────────────────────────────

    def _build_header(self):
        """Header s ORBem, názvem JARVIS a hodinami"""
        hdr = ctk.CTkFrame(self.root, fg_color=BG2, corner_radius=0, height=72)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # Animovaný ORB (stav asistenta)
        self._orb = OrbWidget(hdr)

        ctk.CTkLabel(
            hdr, text="J A R V I S",
            font=("Georgia", 26), text_color=GOLD,
        ).pack(side="left", padx=14)

        right = ctk.CTkFrame(hdr, fg_color=BG2, corner_radius=0)
        right.pack(side="right", padx=16, pady=8)

        self._clock_lbl = ctk.CTkLabel(
            right, text="", font=("DM Sans", 13), text_color=FG,
        )
        self._clock_lbl.pack(anchor="e")

        self.status_lbl = ctk.CTkLabel(
            right, text="● Inicializace",
            font=("DM Sans", 10), text_color=MUTED,
        )
        self.status_lbl.pack(anchor="e")

    # ── TOOLBAR ──────────────────────────────────────────────

    def _build_toolbar(self):
        """Toolbar: TTS, log, paměť, přepínač tématu"""
        tb = ctk.CTkFrame(self.root, fg_color=BG2, corner_radius=0, height=38)
        tb.pack(fill="x")
        tb.pack_propagate(False)

        tts_on = self.tts.is_available()
        self._tts_btn = ctk.CTkButton(
            tb,
            text="🔊 TTS: ZAP" if tts_on else "🔇 TTS: N/A",
            font=("DM Sans", 11),
            fg_color=(GOLD if tts_on else "#444"), hover_color=GOLDH,
            text_color=BG, corner_radius=4, height=26, width=110,
            command=self._toggle_tts,
        )
        self._tts_btn.pack(side="left", padx=8, pady=5)

        for lbl, cmd in [("🗑 Log", self._clear_log), ("🧠 Paměť", self._clear_memory)]:
            ctk.CTkButton(
                tb, text=lbl,
                font=("DM Sans", 11), fg_color="#2a2a2a", hover_color="#444",
                text_color=MUTED, corner_radius=4, height=26, width=82,
                command=cmd,
            ).pack(side="left", padx=2, pady=5)

        # Přepínač dark/light tématu — uloží se do config.json
        self._theme_btn = ctk.CTkButton(
            tb,
            text="☀" if self._dark_mode else "🌙",
            font=("DM Sans", 14), fg_color="#2a2a2a", hover_color="#444",
            text_color=MUTED, corner_radius=4, height=26, width=36,
            command=self._toggle_theme,
        )
        self._theme_btn.pack(side="left", padx=2, pady=5)

    # ── MODEL ROW ────────────────────────────────────────────

    def _build_model_row(self):
        """Výběr Ollama modelu s automatickým uložením"""
        mf = ctk.CTkFrame(self.root, fg_color=BG2, corner_radius=0, height=38)
        mf.pack(fill="x", padx=12, pady=(6, 0))
        mf.pack_propagate(False)

        ctk.CTkLabel(mf, text="Model:", font=("DM Sans", 11), text_color=FG).pack(
            side="left", padx=(0, 6)
        )

        choices = list(AVAILABLE_OLLAMA_MODELS)
        if CONFIG["ollama_model"] not in choices:
            choices.insert(0, CONFIG["ollama_model"])

        self.model_option = ctk.CTkOptionMenu(
            mf, values=choices,
            command=self._on_model_change,
            fg_color=BG, button_color="#333", button_hover_color="#444",
            text_color=FG, dropdown_text_color=FG, width=220,
        )
        self.model_option.set(CONFIG["ollama_model"])
        self.model_option.pack(side="left")

        ctk.CTkLabel(
            mf, text="Uloží se do config.json",
            font=("DM Sans", 10), text_color=MUTED,
        ).pack(side="right")

    # ── CHAT LOG ─────────────────────────────────────────────

    def _build_chat_log(self):
        """Chat log s bublinovým stylem a zvýrazňováním kódu"""
        self.log = ctk.CTkTextbox(
            self.root,
            font=("Consolas", 13),
            fg_color=BG, text_color=FG,
            border_width=0, wrap="word",
            state="disabled",
            spacing1=2, spacing3=2,
        )
        self.log.pack(fill="both", expand=True, padx=0)

        tb = self.log._textbox
        # Uživatelské zprávy — vpravo
        tb.tag_config("ts",          foreground=MUTED,     font=("Consolas", 10))
        tb.tag_config("user_lbl",    foreground="#aaaaaa",  font=("DM Sans", 10, "bold"),
                      justify="right")
        tb.tag_config("user_msg",    foreground=FG,         justify="right", rmargin=8)
        # JARVIS zprávy — vlevo
        tb.tag_config("jarvis_lbl",  foreground=GOLD,       font=("DM Sans", 10, "bold"))
        tb.tag_config("jarvis_msg",  foreground="#ffe0a0")
        # Systémové a ostatní
        tb.tag_config("system_msg",  foreground=MUTED)
        tb.tag_config("error_msg",   foreground=RED)
        tb.tag_config("success_msg", foreground=GREEN)
        tb.tag_config("info_msg",    foreground=BLUE)
        # Kódové bloky — zelená monospace
        tb.tag_config("code",        foreground="#a8d8a8",  font=("Consolas", 12))

    # ── INDETERMINATE PROGRESS BAR ───────────────────────────

    def _build_progress(self):
        """
        Tenký progress bar (2 px, zlatý) pod logem.
        Při idle je neviditelný (progress_color=BG).
        Spustí se s _start_thinking(), zastaví s _stop_thinking().
        """
        self._progress = ctk.CTkProgressBar(
            self.root,
            mode="indeterminate",
            height=2, corner_radius=0,
            fg_color=BG,
            progress_color=BG,     # schovejme při startu
            indeterminate_speed=0.8,
        )
        self._progress.pack(fill="x", padx=0)
        self._progress.set(0)

    # ── KULATÉ MIC TLAČÍTKO ──────────────────────────────────

    def _build_mic_area(self):
        """
        Oblast s kulatým mic tlačítkem (corner_radius=50),
        zlatým rámečkem a stavovým labelem.
        """
        mic_area = ctk.CTkFrame(self.root, fg_color=BG2, corner_radius=0, height=100)
        mic_area.pack(fill="x")
        mic_area.pack_propagate(False)

        # Zlatý rámeček kolem tlačítka
        mic_ring = ctk.CTkFrame(
            mic_area,
            fg_color=BG2,
            border_color=GOLD,
            border_width=2,
            corner_radius=50,
            width=72, height=72,
        )
        mic_ring.place(relx=0.5, rely=0.44, anchor="center")
        mic_ring.pack_propagate(False)

        # Kulaté mic tlačítko
        self.mic_btn = ctk.CTkButton(
            mic_ring,
            text="🎤",
            font=("DM Sans", 22),
            fg_color=GOLD, hover_color=GOLDH, text_color=BG,
            corner_radius=50, width=64, height=64,
            command=self._on_mic_click,
        )
        self.mic_btn.place(relx=0.5, rely=0.5, anchor="center")

        # Stavový label pod tlačítkem
        self._mic_lbl = ctk.CTkLabel(
            mic_area,
            text="Připraven",
            font=("DM Sans", 10), text_color=MUTED,
        )
        self._mic_lbl.place(relx=0.5, rely=0.88, anchor="center")

    # ── INPUT ROW ────────────────────────────────────────────

    def _build_input_row(self):
        """Textový vstup s tlačítkem odeslání"""
        inp = ctk.CTkFrame(self.root, fg_color=BG2, corner_radius=0, height=56)
        inp.pack(fill="x")
        inp.pack_propagate(False)

        self.text_input = ctk.CTkEntry(
            inp,
            placeholder_text="Napiš příkaz pro JARVIS...",
            font=("DM Sans", 14),
            fg_color=BG3, text_color=FG,
            border_color=GOLD, border_width=1,
            corner_radius=6, height=40,
        )
        self.text_input.place(x=12, rely=0.5, anchor="w", relwidth=0.82)
        self.text_input.bind("<Return>", self._on_text_enter)
        self.text_input.focus()

        ctk.CTkButton(
            inp, text="↵",
            font=("Georgia", 20),
            fg_color=GOLD, hover_color=GOLDH, text_color=BG,
            corner_radius=6, width=50, height=40,
            command=self._on_text_enter,
        ).place(relx=0.985, rely=0.5, anchor="e")

    # ── LOG HELPERS ──────────────────────────────────────────

    def _log_user(self, text: str):
        """Zpráva uživatele — zarovnána vpravo s emoji 🧑"""
        ts = datetime.now().strftime("%H:%M")
        tb = self.log._textbox
        self.log.configure(state="normal")
        tb.insert("end", "\n")
        tb.insert("end", f"  {ts}  ", "ts")
        tb.insert("end", "🧑 TY\n", "user_lbl")
        tb.insert("end", f"  {text}\n", "user_msg")
        self.log.configure(state="disabled")
        tb.see("end")

    def _log_jarvis(self, text: str):
        """Celá JARVIS zpráva — vlevo s emoji 🤖 a zvýrazněním kódu"""
        ts = datetime.now().strftime("%H:%M")
        tb = self.log._textbox
        self.log.configure(state="normal")
        tb.insert("end", "\n")
        tb.insert("end", f"  {ts}  ", "ts")
        tb.insert("end", "🤖 JARVIS\n", "jarvis_lbl")

        # Rozdělení na kódové bloky a prostý text
        if "```" in text:
            parts = text.split("```")
            for i, part in enumerate(parts):
                if i % 2 == 0:
                    if part.strip():
                        tb.insert("end", f"  {part}", "jarvis_msg")
                else:
                    lines = part.split("\n")
                    if lines and lines[0].strip() and not lines[0].startswith(" "):
                        lines = lines[1:]
                    tb.insert("end", "\n" + "\n".join(lines) + "\n", "code")
        else:
            tb.insert("end", f"  {text}\n", "jarvis_msg")

        self.log.configure(state="disabled")
        tb.see("end")

    def _log_jarvis_header(self, ts: str):
        """Zobrazí hlavičku JARVIS zprávy pro streaming (jednou na začátku)"""
        tb = self.log._textbox
        self.log.configure(state="normal")
        tb.insert("end", "\n")
        tb.insert("end", f"  {ts}  ", "ts")
        tb.insert("end", "🤖 JARVIS\n  ", "jarvis_lbl")
        self.log.configure(state="disabled")
        tb.see("end")

    def _log_jarvis_chunk(self, text: str):
        """Připojí streamovaný chunk textu k JARVIS zprávě"""
        self.log.configure(state="normal")
        self.log._textbox.insert("end", text + " ", "jarvis_msg")
        self.log.configure(state="disabled")
        self.log._textbox.see("end")

    def _log_system(self, text: str, tag: str = "system_msg"):
        """Systémová zpráva (šedá)"""
        self.log.configure(state="normal")
        self.log._textbox.insert("end", f"\n  {text}\n", tag)
        self.log.configure(state="disabled")
        self.log._textbox.see("end")

    def _log_info(self, text: str):
        self._log_system(f"↳ {text}", "info_msg")

    def _log_error(self, text: str):
        self._log_system(f"❌ {text}", "error_msg")

    def _log_success(self, text: str):
        self._log_system(f"✅ {text}", "success_msg")

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log._textbox.delete("1.0", "end")
        self.log.configure(state="disabled")
        self._log_system("Log vymazán.")

    def _clear_memory(self):
        self.llm.clear_history()
        self._log_system("Paměť rozhovoru vymazána.")

    # ── HODINY ───────────────────────────────────────────────

    def _tick_clock(self):
        self._clock_lbl.configure(text=datetime.now().strftime("%H:%M:%S"))
        if not self._shutdown_event.is_set():
            self.root.after(1000, self._tick_clock)

    # ── ORB + MIC LABEL ──────────────────────────────────────

    def _set_orb(self, state: str):
        """Nastaví stav ORBu (thread-safe přes after)"""
        self.root.after(0, lambda: self._orb.set_state(state))

    def _set_mic_label(self, text: str):
        self.root.after(0, lambda: self._mic_lbl.configure(text=text))

    # ── STATUS ───────────────────────────────────────────────

    def _set_status(self, text: str, color: str = MUTED):
        self.status_lbl.configure(text=text, text_color=color)

    # ── TTS TOGGLE ───────────────────────────────────────────

    def _toggle_tts(self):
        self.tts.enabled = not self.tts.enabled
        self._tts_btn.configure(
            text="🔊 TTS: ZAP" if self.tts.enabled else "🔇 TTS: VYP",
            fg_color=GOLD if self.tts.enabled else "#555",
        )

    # ── TÉMA ─────────────────────────────────────────────────

    def _toggle_theme(self):
        """Přepíná dark/light mód a uloží do config.json"""
        self._dark_mode = not self._dark_mode
        mode = "dark" if self._dark_mode else "light"
        ctk.set_appearance_mode(mode)
        self._theme_btn.configure(text="☀" if self._dark_mode else "🌙")
        CONFIG["theme"] = mode
        try:
            save_config(CONFIG)
        except Exception:
            pass

    # ── MODEL ────────────────────────────────────────────────

    def _on_model_change(self, value: str):
        if not value or value == CONFIG.get("ollama_model"):
            return
        CONFIG["ollama_model"] = value
        self.llm.model = value
        try:
            save_config(CONFIG)
            self._log_success(f"Model přepnut na {value}")
        except Exception as e:
            self._log_error(f"Nelze uložit model: {e}")

    # ── OLLAMA CHECK ─────────────────────────────────────────

    def _check_ollama(self):
        def check():
            if self.llm.is_available():
                self.root.after(0, lambda: self._set_status("● Online", GREEN))
                self.root.after(0, lambda: self._log_success(f"Ollama [{self.llm.model}] ✓"))
            else:
                self.root.after(0, lambda: self._set_status("● Offline", RED))
                self.root.after(0, lambda: self._log_error(
                    "Ollama není dostupná — spusť: ollama serve"
                ))
        threading.Thread(target=check, daemon=True).start()

    # ── THINKING ANIMACE ─────────────────────────────────────

    def _start_thinking(self):
        """Spustí progress bar, animaci tečiček a nastaví ORB na thinking"""
        self._progress.configure(progress_color=GOLD)
        self._progress.start()
        self._set_orb("thinking")
        self._set_mic_label("Zpracovávám...")
        self._dots = 0

        def tick():
            if self._shutdown_event.is_set():
                return
            self._dots = (self._dots + 1) % 4
            self._set_status("● Přemýšlím" + "." * self._dots, BLUE)
            self._thinking_job = self.root.after(400, tick)

        tick()

    def _stop_thinking(self):
        """Zastaví progress bar a animaci tečiček"""
        self._progress.stop()
        self._progress.configure(progress_color=BG)   # schovej
        if self._thinking_job:
            self.root.after_cancel(self._thinking_job)
            self._thinking_job = None

    # ── MIKROFON ─────────────────────────────────────────────

    def _on_mic_click(self):
        if self._is_listening or not self.stt.is_available():
            if not self.stt.is_available():
                self._log_error("Mikrofon není dostupný")
            return
        threading.Thread(target=self._listen_and_process, daemon=True).start()

    def _listen_and_process(self):
        self._is_listening = True
        self._set_orb("listening")
        self._set_mic_label("Poslouchám...")
        self.root.after(0, lambda: self.mic_btn.configure(
            text="⏹", fg_color=RED, hover_color=RED,
        ))
        self.root.after(0, lambda: self._log_system("Poslouchám..."))

        try:
            text = self.stt.listen()
        except Exception as e:
            logger.error(f"STT: {e}")
            self.root.after(0, lambda: self._log_error(f"Chyba mikrofonu: {e}"))
            text = None
        finally:
            self._is_listening = False
            self._set_orb("idle")
            self._set_mic_label("Připraven")
            self.root.after(0, lambda: self.mic_btn.configure(
                text="🎤", fg_color=GOLD, hover_color=GOLDH,
            ))

        if text:
            self._process_command(text)
        else:
            self.root.after(0, lambda: self._log_system("Nerozuměl jsem."))

    # ── TEXT VSTUP ────────────────────────────────────────────

    def _on_text_enter(self, event=None):
        text = self.text_input.get().strip()
        if not text:
            return
        self.text_input.delete(0, "end")
        threading.Thread(target=self._process_command, args=(text,), daemon=True).start()

    # ── ZPRACOVÁNÍ PŘÍKAZU SE STREAMOVÁNÍM ───────────────────

    def _process_command(self, text: str):
        """
        Zpracuje příkaz se streamovanou LLM odpovědí.
        - Každá dokončená věta je ihned přidána do logu a mluvena TTS.
        - COMMAND: detekce přeruší textový stream → vykoná příkaz.
        """
        logger.info(f"Zpracovávám: {text}")
        self.root.after(0, lambda: self._log_user(text))
        self.root.after(0, self._start_thinking)

        try:
            full_response = ""
            sentence_buf  = ""
            header_shown  = False
            is_command    = False

            # ── Streamování odpovědi ─────────────────────────
            for chunk in self.llm.stream_ask(text):
                full_response += chunk

                # Detekce COMMAND: → přeruš textový stream
                if "COMMAND:" in full_response:
                    is_command = True
                    break

                sentence_buf += chunk

                # Zobraz hlavičku JARVIS při první větě
                if not header_shown and sentence_buf.strip():
                    header_shown = True
                    ts = datetime.now().strftime("%H:%M")
                    self.root.after(0, lambda t=ts: self._log_jarvis_header(t))

                # Hledej konce vět → okamžitě mluv
                while True:
                    m = re.search(r"[.!?][\s\n]", sentence_buf)
                    if not m:
                        break
                    sentence      = sentence_buf[: m.end()]
                    sentence_buf  = sentence_buf[m.end():]
                    s = sentence.strip()
                    if s:
                        self.root.after(0, lambda x=s: self._log_jarvis_chunk(x))
                        has_code = any(k in s for k in ("```", "def ", "import "))
                        if not has_code and len(s) < 300:
                            self._set_orb("speaking")
                            self.tts.speak(s)
                            self._set_orb("idle")

            # ── Dočerpej zbytek streamu (po přerušení) ───────
            if is_command:
                for chunk in self.llm.drain_stream():
                    full_response += chunk

            # ── Parsuj finální odpověď ────────────────────────
            message, action_data = self.llm._parse_response(full_response)

            # Zobraz zprávu pokud nebyla streamována (COMMAND odpověď)
            if not header_shown and message:
                self.root.after(0, lambda m=message: self._log_jarvis(m))
                has_code = any(k in message for k in ("```", "def ", "import "))
                if not has_code and len(message) < 300:
                    self._set_orb("speaking")
                    self.tts.speak(message)
                    self._set_orb("idle")
            elif sentence_buf.strip():
                # Zbytek nevypsaného sentence_buf
                self.root.after(0, lambda s=sentence_buf.strip(): self._log_jarvis_chunk(s))
                self.root.after(0, lambda: self.log._textbox.insert("end", "\n"))

            # ── Vykonej příkaz ────────────────────────────────
            action = action_data.get("action", "answer")
            params = action_data.get("params", {})

            if action not in ("answer", ""):
                # Pokud model vrátil zprávu pro příkaz, zobraz ji
                cmd_msg = action_data.get("message") or self.llm._default_message(action, "")
                if cmd_msg and not header_shown:
                    self.root.after(0, lambda m=cmd_msg: self._log_jarvis(m))
                    if len(cmd_msg) < 300:
                        self._set_orb("speaking")
                        self.tts.speak(cmd_msg)
                        self._set_orb("idle")

                self.root.after(0, lambda: self._log_info(f"akce: {action} {params}"))
                result = self.commands.execute(action, params)
                if result and result != "ok":
                    self.root.after(0, lambda r=result: self._log_info(r))

        except Exception as e:
            logger.error(f"Chyba zpracování: {e}", exc_info=True)
            self.root.after(0, lambda: self._log_error("Chyba, zkus to znovu."))
        finally:
            self.root.after(0, self._stop_thinking)
            self._set_orb("idle")
            self._set_mic_label("Připraven")
            self.root.after(0, lambda: self._set_status("● Online", GREEN))

    # ── SHUTDOWN ─────────────────────────────────────────────

    def _signal_handler(self, signum, frame):
        logger.info(f"Signál {signum}")
        self._shutdown()

    def _on_close(self):
        self._shutdown()

    def _shutdown(self):
        logger.info("Ukončuji JARVIS...")
        self._shutdown_event.set()
        self._orb.stop()
        self._stop_thinking()
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self._shutdown()
        except Exception as e:
            logger.error(f"Nezachycená chyba: {e}")
            self._shutdown()


# ══════════════════════════════════════════════════════
#  SPUŠTĚNÍ
# ══════════════════════════════════════════════════════

def main():
    try:
        app = JarvisApp()
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Fatální chyba: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
