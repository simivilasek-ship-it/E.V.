"""
E.V. v3.0 — Wake word detektor
Detekuje klíčové slovo "JARVISe" pro probuzení asistenta.

Používá porpoise (lehký) nebo fallback na SpeechRecognition.
"""

import time
import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)

# Zkusit porpoise (nejlehčí)
try:
    import porpoise
    HAS_PORPOISE = True
except ImportError:
    HAS_PORPOISE = False

# Fallback: SpeechRecognition
try:
    import speech_recognition as sr
    HAS_SR = True
except ImportError:
    HAS_SR = False


class WakeWordDetector:
    """
    Detekuje wake word "JARVISe" v pozadí.
    pause() / resume() uvolní mikrofon když STT poslouchá příkaz.

    Používá:
    1. porpoise (nejlehčí, nejrychlejší)
    2. Fallback: SpeechRecognition s detekcí klíčových slov
    """

    def __init__(
        self,
        wake_word: str = "jarvis",
        on_wake: Callable = None,
        sensitivity: float = 0.5,
    ):
        self.wake_word = wake_word.lower()
        self.on_wake = on_wake
        self.sensitivity = sensitivity

        self._running = False
        self._paused  = threading.Event()   # set = aktivní, clear = pauza
        self._paused.set()                  # výchozí stav: aktivní
        self._thread  = None
        self._detector = None
        
        # Inicializovat detektor
        self._init_detector()
    
    def _init_detector(self):
        """Inicializuje wake word detektor"""
        if HAS_PORPOISE:
            try:
                # porpoise používá jednoduchý model
                self._detector = porpoise.Porpoise(
                    keywords=[self.wake_word],
                    sensitivity=self.sensitivity,
                )
                logger.info(f"Wake word detektor: porpoise (slovo: {self.wake_word})")
                return
            except Exception as e:
                logger.warning(f"porpoise selhal: {e}")
        
        if HAS_SR:
            logger.info("Wake word detektor: SpeechRecognition fallback")
            return
        
        logger.warning("Wake word detektor není k dispozici. Instaluj: pip install porpoise")
    
    def start(self):
        """Spustí detekci wake slova v pozadí"""
        if self._running:
            return
        
        if not self._detector and not HAS_SR:
            logger.warning("Wake word detektor není k dispozici")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(f"Wake word detektor spuštěn (slovo: '{self.wake_word}')")
    
    def pause(self) -> None:
        """Pozastaví detekci — mikrofon uvolněn pro STT."""
        self._paused.clear()
        logger.debug("Wake word detektor pozastaven")

    def resume(self) -> None:
        """Obnoví detekci po dokončení STT příkazu."""
        self._paused.set()
        logger.debug("Wake word detektor obnoven")

    def stop(self) -> None:
        """Zastaví detekci úplně."""
        self._running = False
        self._paused.set()   # odblokuj čekající vlákno aby mohlo skončit
        logger.debug("Wake word detektor zastaven")
    
    def _run(self):
        """Hlavní smyčka detekce"""
        if self._detector:
            self._run_porpoise()
        elif HAS_SR:
            self._run_sr_fallback()
    
    def _run_porpoise(self):
        """Detekce pomocí porpoise"""
        try:
            while self._running:
                self._paused.wait()          # čekej pokud je pauza
                if not self._running:
                    break
                result = self._detector.listen(timeout=0.5)
                if result and result.keyword == self.wake_word:
                    logger.info(f"Wake word detekován: '{self.wake_word}'")
                    if self.on_wake:
                        self.on_wake()
        except Exception as e:
            logger.error(f"porpoise chyba: {e}")

    def _run_sr_fallback(self):
        """Fallback detekce pomocí SpeechRecognition"""
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True

        while self._running:
            self._paused.wait()              # čekej pokud je pauza (STT poslouchá)
            if not self._running:
                break
            try:
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    audio = recognizer.listen(source, timeout=1, phrase_time_limit=3)

                try:
                    text = recognizer.recognize_google(audio, language="cs-CZ")
                    if self.wake_word in text.lower():
                        logger.info(f"Wake word detekován: '{text}'")
                        if self.on_wake:
                            self.on_wake()
                except sr.UnknownValueError:
                    pass
                except sr.RequestError:
                    pass
            except sr.WaitTimeoutError:
                pass
            except Exception as e:
                logger.error(f"SR fallback chyba: {e}")
                time.sleep(1)