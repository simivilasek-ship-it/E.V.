"""
JARVIS v2.0 — Text-to-Speech (TTS)
Syntéza řeči pomocí edge-tts nebo pyttsx3
"""

import asyncio
import logging
import tempfile
import subprocess
import os
import threading
from typing import Optional

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    HAS_PYTTSX3 = False

logger = logging.getLogger(__name__)

class TTSEngine:
    """Engine pro syntézu řeči"""

    def __init__(self, config: dict):
        self.config = config
        self.enabled = config.get("tts_enabled", True)
        self.voice = config.get("tts_voice", "cs-CZ-AntoninNeural")
        self.rate = config.get("tts_rate", 170)

        # Najdi audio přehrávač pro Linux
        self._player = self._find_player()

        # Pyttsx3 fallback
        self._pyttsx3_engine = None
        self._has_pyttsx3 = False
        if HAS_PYTTSX3:
            try:
                self._pyttsx3_engine = pyttsx3.init()
                self._pyttsx3_engine.setProperty("rate", self.rate)
                # Najdi český hlas
                for voice in self._pyttsx3_engine.getProperty("voices"):
                    if any(x in (voice.id + voice.name).lower() for x in ("czech", "cs-cz", "zuzana", "jakub")):
                        self._pyttsx3_engine.setProperty("voice", voice.id)
                        break
                self._has_pyttsx3 = True
                logger.info("Pyttsx3 TTS inicializován")
            except Exception as e:
                logger.warning(f"Pyttsx3 inicializace selhala: {e}")

        if HAS_EDGE_TTS:
            logger.info("Edge-tts TTS inicializován")
        elif self._has_pyttsx3:
            logger.info("Používám pyttsx3 jako fallback")
        else:
            logger.warning("Žádný TTS engine není dostupný")

    def _find_player(self) -> Optional[str]:
        """Najde audio přehrávač na Linuxu"""
        for player in ("mpg123", "ffplay", "cvlc", "mplayer"):
            if subprocess.run(["which", player], capture_output=True, text=True).returncode == 0:
                return player
        return None

    async def _speak_edge_tts(self, text: str) -> None:
        """Syntéza pomocí edge-tts"""
        try:
            communicate = edge_tts.Communicate(text, self.voice)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_path = f.name

            await communicate.save(temp_path)

            try:
                if os.name == "nt":  # Windows
                    subprocess.run(["start", "/wait", "", temp_path], shell=True, check=True)
                else:  # Linux/Mac
                    if self._player == "ffplay":
                        subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", temp_path], check=True)
                    elif self._player:
                        subprocess.run([self._player, "-q", temp_path], check=True)
                    else:
                        logger.error("Žádný audio přehrávač nenalezen")
            finally:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Edge-tts chyba: {e}")
            raise

    def _speak_pyttsx3(self, text: str) -> None:
        """Syntéza pomocí pyttsx3"""
        try:
            if self._pyttsx3_engine:
                self._pyttsx3_engine.say(text)
                self._pyttsx3_engine.runAndWait()
            else:
                raise RuntimeError("Pyttsx3 engine není inicializován")
        except Exception as e:
            logger.error(f"Pyttsx3 chyba: {e}")
            raise

    def speak(self, text: str) -> None:
        """Přečte text hlasem"""
        if not self.enabled or not text:
            return

        def _run():
            try:
                if HAS_EDGE_TTS:
                    asyncio.run(self._speak_edge_tts(text))
                elif self._has_pyttsx3:
                    self._speak_pyttsx3(text)
                else:
                    logger.warning("TTS není dostupný")
            except Exception as e:
                logger.error(f"TTS selhal: {e}")

        # Spusť v samostatném vlákně
        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def is_available(self) -> bool:
        """Vrátí True pokud TTS funguje"""
        return self.enabled and (HAS_EDGE_TTS or self._has_pyttsx3)