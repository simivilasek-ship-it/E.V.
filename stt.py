"""
JARVIS v3.0 — Speech-to-Text (STT)
Rozpoznávání řeči s podporou více jazyků
"""

import logging
from typing import Optional

try:
    import speech_recognition as sr
    HAS_STT = True
except ImportError:
    HAS_STT = False
    sr = None

logger = logging.getLogger(__name__)

class STTEngine:
    """Engine pro rozpoznávání řeči s multi-language supportem"""

    def __init__(self, config: dict):
        self.config = config
        self.recognizer = None
        self.language = config.get("stt_language", "cs-CZ")

        if HAS_STT:
            self.recognizer = sr.Recognizer()
            self.recognizer.pause_threshold = 1.0
            self.recognizer.energy_threshold = config.get("stt_energy_threshold", 300)
            self.recognizer.dynamic_energy_threshold = True
            logger.info(f"STT engine inicializován (jazyk: {self.language})")
        else:
            logger.warning("SpeechRecognition není nainstalován - STT nebude fungovat")

    def set_language(self, language_code: str) -> bool:
        """Změní jazyk rozpoznávání řeči."""
        available = self.config.get("available_languages", {})
        if language_code not in available:
            logger.warning(f"Jazyk {language_code} není dostupný")
            return False
        self.language = language_code
        self.config["stt_language"] = language_code
        logger.info(f"Jazyk změněn na {language_code}")
        return True

    def get_language(self) -> str:
        """Vrátí aktuálně nastaveného jazyka."""
        return self.language

    def listen(self) -> Optional[str]:
        """
        Poslouchá mikrofon a vrátí rozpoznaný text
        Returns None při chybě nebo prázdném vstupu
        """
        if not HAS_STT or not self.recognizer:
            logger.error("STT není dostupný")
            return None

        try:
            with sr.Microphone() as source:
                logger.debug("Přizpůsobuji se okolnímu hluku...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)

                logger.info(f"Poslouchám... ({self.language})")
                audio = self.recognizer.listen(
                    source,
                    timeout=self.config.get("stt_timeout", 10),
                    phrase_time_limit=self.config.get("stt_phrase_limit", 15)
                )

            # Primární rozpoznávání (Google)
            try:
                text = self.recognizer.recognize_google(audio, language=self.language)
                logger.info(f"Rozpoznáno: {text}")
                return text
            except sr.UnknownValueError:
                logger.warning("Nerozuměl jsem - zkouším offline...")
                # Fallback na offline rozpoznávání (omezeno na češtinu)
                try:
                    if self.language.startswith("cs"):
                        text = self.recognizer.recognize_sphinx(audio, language="cs-CZ")
                        logger.info(f"Offline rozpoznáno: {text}")
                        return text
                    else:
                        logger.warning(f"Offline rozpoznávání není dostupné pro {self.language}")
                        return None
                except sr.UnknownValueError:
                    logger.warning("Offline rozpoznávání také selhalo")
                    return None

        except sr.WaitTimeoutError:
            logger.warning("Timeout - žádný zvuk")
            return None
        except sr.RequestError as e:
            logger.error(f"Chyba Google STT API: {e}")
            return None
        except Exception as e:
            logger.error(f"Chyba mikrofonu: {e}")
            return None

    def is_available(self) -> bool:
        """Ověří dostupnost mikrofonu."""
        if not HAS_STT:
            return False
        try:
            with sr.Microphone() as source:
                logger.debug("Mikrofon dostupný")
                return True
        except Exception as e:
            logger.error(f"Mikrofon není dostupný: {e}")
            return False


    def is_available(self) -> bool:
        """Vrátí True pokud STT funguje"""
        return HAS_STT and self.recognizer is not None