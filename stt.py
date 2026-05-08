"""
JARVIS v2.0 — Speech-to-Text (STT)
Rozpoznávání řeči pomocí SpeechRecognition
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
    """Engine pro rozpoznávání řeči"""

    def __init__(self, config: dict):
        self.config = config
        self.recognizer = None

        if HAS_STT:
            self.recognizer = sr.Recognizer()
            self.recognizer.pause_threshold = 1.0
            self.recognizer.energy_threshold = config.get("stt_energy_threshold", 300)
            self.recognizer.dynamic_energy_threshold = True
            logger.info("STT engine inicializován")
        else:
            logger.warning("SpeechRecognition není nainstalován - STT nebude fungovat")

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

                logger.info("Poslouchám...")
                audio = self.recognizer.listen(
                    source,
                    timeout=self.config.get("stt_timeout", 10),
                    phrase_time_limit=self.config.get("stt_phrase_limit", 15)
                )

            # Primární rozpoznávání (Google)
            try:
                text = self.recognizer.recognize_google(audio, language="cs-CZ")
                logger.info(f"Rozpoznáno: {text}")
                return text
            except sr.UnknownValueError:
                logger.warning("Nerozuměl jsem - zkouším offline...")
                # Fallback na offline rozpoznávání
                try:
                    text = self.recognizer.recognize_sphinx(audio, language="cs-CZ")
                    logger.info(f"Offline rozpoznáno: {text}")
                    return text
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
        """Vrátí True pokud STT funguje"""
        return HAS_STT and self.recognizer is not None