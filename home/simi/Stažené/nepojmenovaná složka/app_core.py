"""
JARVIS v3.0 — Aplikační jádro
Propojuje GUI, LLM, CommandExecutor a paměť dohromady.
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional

from config import load_config, save_config, CONFIG
from gui import JarvisGUI
from llm import LLMEngine
from commands import CommandExecutor
from memory import JarvisMemory
from idle_detector import IdleDetector
from wake_word_detector import WakeWordDetector

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════
#  NASTAVENÍ LOGOVÁNÍ
# ══════════════════════════════════════════════════════

def setup_logging(config: dict):
    """Nastaví logování podle konfigurace"""
    level = getattr(logging, config.get("log_level", "INFO"), logging.INFO)
    log_file = os.path.join(os.path.dirname(__file__), "jarvis.log")
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger.info(f"Logování inicializováno (úroveň: {config.get('log_level', 'INFO')})")

# ══════════════════════════════════════════════════════
#  JARVIS APP
# ══════════════════════════════════════════════════════

class JarvisApp:
    """
    Hlavní třída aplikace.
    Vytvoří a propojí všechny komponenty.
    """
    
    def __init__(self):
        # Načíst konfiguraci
        self.config = load_config()
        setup_logging(self.config)
        
        logger.info("Inicializuji JARVIS v3.0...")
        
        # Inicializovat komponenty
        self.memory = JarvisMemory(self.config)
        self.executor = CommandExecutor(self.config)
        self.llm = LLMEngine(self.config, self.memory)
        
        # Inicializovat GUI
        self.gui = JarvisGUI()
        
        # Propojit callbacky
        self.gui.on_mic_click = self._on_mic_click
        self.gui.on_send = self._on_send
        self.gui.on_model_change = self._on_model_change
        
        # Inicializovat detektory
        self.idle_detector = IdleDetector(
            idle_timeout=30,  # 30 vteřin nečinnosti → idle mód
            on_idle=self._on_idle,
            on_active=self._on_active,
        )
        self.wake_detector = WakeWordDetector(
            wake_word="jarvis",
            on_wake=self._on_wake,
        )
        
        # Stav
        self._listening = False
        self._is_idle = False
        
        # Zkontrolovat Ollama
        self._check_ollama()
        
        # Spustit idle detektor
        self.idle_detector.start()
        
        logger.info("JARVIS v3.0 inicializován.")
    
    # ── SPUŠTĚNÍ ────────────────────────────────────
    
    def run(self):
        """Spustí hlavní smyčku GUI"""
        try:
            self.gui.run()
        except KeyboardInterrupt:
            logger.info("Ukončuji JARVIS...")
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Úklid při ukončení"""
        self.idle_detector.stop()
        self.wake_detector.stop()
        logger.info("JARVIS ukončen.")
    
    # ── OLLAMA CHECK ────────────────────────────────
    
    def _check_ollama(self):
        """Zkontroluje dostupnost Ollamy"""
        def _check():
            try:
                available = self.llm.is_available()
                if available:
                    self.gui.set_status("Ollama online ✓")
                    self.gui.set_state("idle")
                    logger.info(f"Ollama [{self.config.get('ollama_model')}] připojena")
                else:
                    self.gui.set_status("⚠️ Model nenalezen")
                    logger.warning(f"Model '{self.config.get('ollama_model')}' není v Ollamě")
            except Exception as e:
                self.gui.set_status("⚠️ Ollama offline")
                logger.error(f"Ollama nedostupná: {e}")
        
        import threading
        threading.Thread(target=_check, daemon=True).start()
    
    # ── CALLBACKY ───────────────────────────────────
    
    def _on_mic_click(self):
        """Uživatel kliknul na mikrofon"""
        if self._listening:
            return
        
        # Probudit se z idle
        self._exit_idle()
        
        import threading
        threading.Thread(target=self._listen_and_process, daemon=True).start()
    
    def _on_send(self, text: str):
        """Uživatel odeslal text"""
        # Probudit se z idle
        self._exit_idle()
        
        self.gui.add_message(text, "user")
        self.gui.set_state("thinking")
        
        import threading
        threading.Thread(target=self._process_text, args=(text,), daemon=True).start()
    
    def _on_model_change(self, model: str):
        """Uživatel změnil model"""
        self.config["ollama_model"] = model
        save_config(self.config)
        self.llm.model = model
        logger.info(f"Model změněn na: {model}")
    
    def _on_idle(self):
        """Detekována nečinnost → přepnout do idle módu"""
        if not self._is_idle and not self._listening:
            self._is_idle = True
            self.gui.set_state("idle")
            self.gui.orb.set_speed(0.3)  # Zpomalit orb
            logger.debug("Idle mód aktivován")
    
    def _on_active(self):
        """Uživatel je aktivní → vypnout idle mód"""
        self._exit_idle()
    
    def _exit_idle(self):
        """Opustit idle mód"""
        if self._is_idle:
            self._is_idle = False
            self.gui.orb.set_speed(1.0)  # Obnovit rychlost orbu
            self.gui.set_state("idle")
            logger.debug("Idle mód deaktivován")
    
    def _on_wake(self):
        """Rozpoznáno wake slovo 'JARVISe'"""
        logger.info("Wake word detected")
        self._exit_idle()
        self.gui.set_state("listening")
        self.gui.set_status("Poslouchám...")
        
        # Automaticky začít poslouchat
        import threading
        threading.Thread(target=self._listen_and_process, daemon=True).start()
    
    # ── ZPRACOVÁNÍ ──────────────────────────────────
    
    def _listen_and_process(self):
        """Poslechne mikrofon a zpracuje příkaz"""
        self._listening = True
        self.gui.set_state("listening")
        self.gui.set_status("Poslouchám...")
        
        try:
            from stt import listen_microphone
            text = listen_microphone()
        except Exception as e:
            logger.error(f"Chyba mikrofonu: {e}")
            text = ""
        finally:
            self._listening = False
        
        if text:
            self.gui.add_message(text, "user")
            self._process_text(text)
        else:
            self.gui.set_status("Nerozuměl jsem")
            self.gui.set_state("idle")
    
    def _process_text(self, text: str):
        """Zpracuje text příkazu"""
        self.gui.set_state("thinking")
        
        try:
            # Získat odpověď od LLM (včetně lokálního routeru)
            message, action_data = self.llm.ask(text)
            
            # Zobrazit zprávu
            if message:
                self.gui.add_message(message, "jarvis")
            
            # Vykonat akci (pokud není answer)
            action = action_data.get("action", "answer")
            if action != "answer":
                params = action_data.get("params", {})
                logger.info(f"Akce: {action} {params}")
                
                result = self.executor.execute(action, params)
                if result and result != "ok":
                    self.gui.add_message(f"✓ {result}", "jarvis")
            
            self.gui.set_state("idle")
            self.gui.set_status("Připraven")
            
        except Exception as e:
            logger.error(f"Chyba zpracování: {e}")
            self.gui.add_message(f"Chyba: {e}", "jarvis")
            self.gui.set_state("idle")
            self.gui.set_status("Chyba")
        
        # Resetovat idle timer
        self.idle_detector.reset()


# ══════════════════════════════════════════════════════
#  SPUŠTĚNÍ
# ══════════════════════════════════════════════════════

if __name__ == "__main__":
    app = JarvisApp()
    app.run()