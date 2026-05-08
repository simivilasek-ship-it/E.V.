"""
JARVIS v2.0 — Hlasový asistent
Hlavní orchestrátor aplikace
"""

import logging
import sys
import signal
import threading
import time
from typing import Optional

# Import modulů
from config import CONFIG
from stt import STTEngine
from tts import TTSEngine
from llm import LLMEngine
from commands import CommandExecutor

# GUI
import customtkinter as ctk
from datetime import datetime

# ══════════════════════════════════════════════════════
#  KONSTANTY
# ══════════════════════════════════════════════════════

GOLD = "#b06d00"
GOLDH = "#c87f10"
BG = "#0f0d0a"
BG2 = "#1a1510"
FG = "#f0ead8"
MUTED = "#888888"

# ══════════════════════════════════════════════════════
#  HLAVNÍ APLIKACE
# ══════════════════════════════════════════════════════

class JarvisApp:
    """Hlavní aplikace JARVIS"""

    def __init__(self):
        # Nastav logging
        self._setup_logging()

        logger.info("Spouštím JARVIS v2.0...")

        # Inicializuj komponenty
        try:
            self.stt = STTEngine(CONFIG)
            self.tts = TTSEngine(CONFIG)
            self.llm = LLMEngine(CONFIG)
            self.commands = CommandExecutor(CONFIG)
            logger.info("Všechny komponenty inicializovány")
        except Exception as e:
            logger.error(f"Chyba inicializace: {e}")
            sys.exit(1)

        # Stav
        self._is_listening = False
        self._thinking_job: Optional[threading.Timer] = None
        self._shutdown_event = threading.Event()

        # GUI
        self._setup_gui()

        # Signal handling pro graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Kontrola Ollama
        self.after(300, self._check_ollama)

        logger.info("JARVIS připraven")

    def _setup_logging(self):
        """Nastaví logging"""
        level = getattr(logging, CONFIG.get("log_level", "INFO").upper())
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('jarvis.log', encoding='utf-8')
            ]
        )

    def _setup_gui(self):
        """Nastaví GUI"""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.root = ctk.CTk()
        self.root.title("JARVIS v2.0")
        self.root.geometry(CONFIG["window_size"])
        self.root.minsize(420, 580)
        self.root.configure(fg_color=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()

    def _build_ui(self):
        """Sestaví UI"""
        # Header
        hdr = ctk.CTkFrame(self.root, fg_color=BG2, corner_radius=0, height=72)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr, text="J A R V I S",
            font=("Georgia", 26), text_color=GOLD,
        ).pack(side="left", padx=22)

        right = ctk.CTkFrame(hdr, fg_color=BG2, corner_radius=0)
        right.pack(side="right", padx=16, pady=8)

        self._clock_lbl = ctk.CTkLabel(
            right, text="", font=("DM Sans", 12), text_color=FG,
        )
        self._clock_lbl.pack(anchor="e")

        self.status_lbl = ctk.CTkLabel(
            right, text="● Inicializace", font=("DM Sans", 11), text_color=MUTED,
        )
        self.status_lbl.pack(anchor="e")

        # Toolbar
        tb = ctk.CTkFrame(self.root, fg_color=BG2, corner_radius=0, height=40)
        tb.pack(fill="x")
        tb.pack_propagate(False)

        self._tts_btn = ctk.CTkButton(
            tb, text=("🔊 TTS: ZAP" if self.tts.is_available() else "🔇 TTS: N/A"),
            font=("DM Sans", 11),
            fg_color=(GOLD if self.tts.is_available() else "#444"),
            hover_color=GOLDH,
            text_color=BG, corner_radius=0, height=28, width=110,
            command=self._toggle_tts,
        )
        self._tts_btn.pack(side="left", padx=8, pady=5)

        for label, cmd in [("🗑 Log", self._clear_log), ("🧠 Paměť", self._clear_memory)]:
            ctk.CTkButton(
                tb, text=label,
                font=("DM Sans", 11), fg_color="#333", hover_color="#555",
                text_color=FG, corner_radius=0, height=28, width=80,
                command=cmd,
            ).pack(side="left", padx=2, pady=5)

        self._vol_lbl = ctk.CTkLabel(tb, text="", font=("DM Sans", 11), text_color=MUTED)
        self._vol_lbl.pack(side="right", padx=12)

        # Divider
        ctk.CTkFrame(self.root, fg_color=GOLD, height=1, corner_radius=0).pack(fill="x")

        # Log
        self.log = ctk.CTkTextbox(
            self.root,
            font=("Consolas", 13),
            fg_color=BG, text_color=FG,
            border_width=0, wrap="word",
            state="disabled",
        )
        self.log.pack(fill="both", expand=True, padx=14, pady=(10, 4))

        self.log._textbox.tag_config("accent", foreground=GOLD)
        self.log._textbox.tag_config("muted", foreground=MUTED)
        self.log._textbox.tag_config("success", foreground="#4caf50")
        self.log._textbox.tag_config("error", foreground="#e53935")
        self.log._textbox.tag_config("user", foreground=FG)
        self.log._textbox.tag_config("info", foreground="#64b5f6")

        # Divider
        ctk.CTkFrame(self.root, fg_color=GOLD, height=1, corner_radius=0).pack(fill="x")

        # Mic button
        btn_frame = ctk.CTkFrame(self.root, fg_color=BG2, corner_radius=0, height=110)
        btn_frame.pack(fill="x")
        btn_frame.pack_propagate(False)

        self.mic_btn = ctk.CTkButton(
            btn_frame,
            text="🎤  MLUVIT",
            font=("Georgia", 17),
            fg_color=GOLD, hover_color=GOLDH, text_color=BG,
            corner_radius=0, height=64, width=240,
            command=self._on_mic_click,
        )
        self.mic_btn.place(relx=0.5, rely=0.5, anchor="center")

        # Text input
        inp = ctk.CTkFrame(self.root, fg_color=BG2, corner_radius=0, height=56)
        inp.pack(fill="x")
        inp.pack_propagate(False)

        self.text_input = ctk.CTkEntry(
            inp,
            placeholder_text="Nebo napište příkaz...",
            font=("DM Sans", 13),
            fg_color=BG, text_color=FG,
            border_color=GOLD, border_width=1,
            corner_radius=0, height=36,
        )
        self.text_input.place(x=12, rely=0.5, anchor="w", relwidth=0.78)
        self.text_input.bind("<Return>", self._on_text_enter)

        ctk.CTkButton(
            inp, text="↵",
            font=("Georgia", 18),
            fg_color=GOLD, hover_color=GOLDH, text_color=BG,
            corner_radius=0, width=48, height=36,
            command=self._on_text_enter,
        ).place(relx=0.98, rely=0.5, anchor="e")

        self._log("JARVIS v2.0 spuštěn.", "accent")
        self._log("Klikni na MLUVIT nebo napiš příkaz.\n", "muted")
        self._tick_clock()
        self._refresh_vol()

    def _tick_clock(self):
        """Aktualizuje hodiny"""
        self._clock_lbl.configure(text=datetime.now().strftime("%H:%M:%S"))
        if not self._shutdown_event.is_set():
            self.root.after(1000, self._tick_clock)

    def _refresh_vol(self):
        """Aktualizuje zobrazení hlasitosti"""
        # Zde by mohla být implementace získání aktuální hlasitosti
        if not self._shutdown_event.is_set():
            self.root.after(5000, self._refresh_vol)

    def _log(self, text: str, tag: str = "user"):
        """Přidá zprávu do logu"""
        self.log.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self.log._textbox.insert("end", f"[{ts}] ", "muted")
        self.log._textbox.insert("end", text + "\n", tag)
        self.log.configure(state="disabled")
        self.log._textbox.see("end")

    def _clear_log(self):
        """Vymaže log"""
        self.log.configure(state="normal")
        self.log._textbox.delete("1.0", "end")
        self.log.configure(state="disabled")
        self._log("Log vymazán.", "muted")

    def _clear_memory(self):
        """Vymaže historii konverzace"""
        self.llm.clear_history()
        self._log("Paměť rozhovoru vymazána.", "muted")

    def _set_status(self, text: str, color: str = MUTED):
        """Nastaví status"""
        self.status_lbl.configure(text=text, text_color=color)

    def _toggle_tts(self):
        """Přepne TTS"""
        self.tts.enabled = not self.tts.enabled
        self._tts_btn.configure(
            text="🔊 TTS: ZAP" if self.tts.enabled else "🔇 TTS: VYP",
            fg_color=GOLD if self.tts.enabled else "#555",
        )

    def _check_ollama(self):
        """Zkontroluje Ollama"""
        def check():
            if self.llm.is_available():
                self.root.after(0, lambda: self._set_status("● Online", "#4caf50"))
                self.root.after(0, lambda: self._log(f"Ollama [{self.llm.model}] ✓", "success"))
            else:
                self.root.after(0, lambda: self._set_status("● Offline", "#e53935"))
                self.root.after(0, lambda: self._log("Ollama není dostupná — spusť: ollama serve", "error"))

        threading.Thread(target=check, daemon=True).start()

    def _start_thinking(self):
        """Spustí animaci přemýšlení"""
        self._dots = 0
        def tick():
            if self._shutdown_event.is_set():
                return
            self._dots = (self._dots + 1) % 4
            self._set_status("● Přemýšlím" + "." * self._dots, GOLD)
            self._thinking_job = self.root.after(400, tick)
        tick()

    def _stop_thinking(self):
        """Zastaví animaci přemýšlení"""
        if self._thinking_job:
            self.root.after_cancel(self._thinking_job)
            self._thinking_job = None

    def _on_mic_click(self):
        """Klik na mikrofon"""
        if self._is_listening or not self.stt.is_available():
            return

        threading.Thread(target=self._listen_and_process, daemon=True).start()

    def _listen_and_process(self):
        """Poslouchá a zpracuje příkaz"""
        self._is_listening = True
        self.root.after(0, lambda: self.mic_btn.configure(
            text="⏺  POSLOUCHÁM...", fg_color="#e53935", state="disabled",
        ))
        self.root.after(0, lambda: self._log("Poslouchám...", "muted"))

        try:
            text = self.stt.listen()
        except Exception as e:
            logger.error(f"STT chyba: {e}")
            self.root.after(0, lambda: self._log(f"Chyba mikrofonu: {e}", "error"))
            text = None
        finally:
            self._is_listening = False
            self.root.after(0, lambda: self.mic_btn.configure(
                text="🎤  MLUVIT", fg_color=GOLD, state="normal",
            ))

        if text:
            self._process_command(text)
        else:
            self.root.after(0, lambda: self._log("Nerozuměl jsem. Zkus znovu.", "muted"))

    def _on_text_enter(self, event=None):
        """Enter v text poli"""
        text = self.text_input.get().strip()
        if not text:
            return
        self.text_input.delete(0, "end")
        threading.Thread(target=self._process_command, args=(text,), daemon=True).start()

    def _process_command(self, text: str):
        """Zpracuje příkaz"""
        logger.info(f"Zpracovávám: {text}")
        self.root.after(0, lambda: self._log(f"Ty: {text}", "user"))
        self.root.after(0, self._start_thinking)

        try:
            # Zeptej se LLM
            message, action_data = self.llm.ask(text)

            # Řekni odpověď
            if message:
                self.root.after(0, lambda: self._log(f"JARVIS: {message}", "accent"))
                self.tts.speak(message)

            # Vykonej akci
            action = action_data.get("action", "answer")
            params = action_data.get("params", {})

            if action != "answer":
                def notify(msg, tag="info"):
                    self.root.after(0, lambda: self._log(msg, tag))

                result = self.commands.execute(action, params)
                if result and result != "ok":
                    self.root.after(0, lambda: self._log(f"→ {result}", "info"))

        except Exception as e:
            logger.error(f"Chyba při zpracování příkazu: {e}")
            error_msg = "Došlo k chybě, zkus to znovu."
            self.root.after(0, lambda: self._log(error_msg, "error"))
            self.tts.speak(error_msg)
        finally:
            self.root.after(0, self._stop_thinking)
            self.root.after(0, lambda: self._set_status("● Online", "#4caf50"))

    def _signal_handler(self, signum, frame):
        """Handler pro signály (Ctrl+C)"""
        logger.info(f"Dostal signál {signum}, ukončuji...")
        self._shutdown()

    def _on_close(self):
        """Handler pro zavření okna"""
        self._shutdown()

    def _shutdown(self):
        """Graceful shutdown"""
        logger.info("Ukončuji JARVIS...")
        self._shutdown_event.set()

        # Zastav animace
        self._stop_thinking()

        # Ukonči GUI
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass

        logger.info("JARVIS ukončen")

    def run(self):
        """Spustí aplikaci"""
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
    """Hlavní funkce"""
    try:
        app = JarvisApp()
        app.run()
    except KeyboardInterrupt:
        logger.info("Přerušen uživatelem")
    except Exception as e:
        logger.error(f"Fatální chyba: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
