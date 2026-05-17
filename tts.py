"""
JARVIS v4.2 — Text-to-Speech (TTS)
Jeden worker vlákno + queue → věty se přehrávají sériově,
žádné souběžné přehrávání, žádné blokování více vláken.
"""

import asyncio
import logging
import queue
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

_STOP_SENTINEL = object()  # speciální hodnota pro zastavení workeru


class TTSEngine:
    """Engine pro syntézu řeči — jeden worker, neblokující fronta."""

    def __init__(self, config: dict):
        self.config = config
        self.enabled = config.get("tts_enabled", True)
        self.voice   = config.get("tts_voice", "cs-CZ-AntoninNeural")
        self.rate    = config.get("tts_rate", 170)

        self._queue:        queue.Queue = queue.Queue()
        self._current_proc: Optional[subprocess.Popen] = None
        self._worker:       Optional[threading.Thread] = None
        self._running:      bool = False

        self._player = self._find_player()
        self._pyttsx3_engine = None
        self._has_pyttsx3 = False

        # Streaming je výchozí pokud ffplay je dostupný
        self._streaming_enabled = (self._player == "ffplay") and config.get("tts_streaming", True)
        if self._streaming_enabled:
            logger.info("TTS: streaming mód aktivní (nižší latence)")

        if HAS_PYTTSX3:
            try:
                self._pyttsx3_engine = pyttsx3.init()
                self._pyttsx3_engine.setProperty("rate", self.rate)
                for voice in self._pyttsx3_engine.getProperty("voices"):
                    if any(x in (voice.id + voice.name).lower()
                           for x in ("czech", "cs-cz", "zuzana", "jakub")):
                        self._pyttsx3_engine.setProperty("voice", voice.id)
                        break
                self._has_pyttsx3 = True
            except Exception as e:
                logger.warning(f"Pyttsx3 init selhal: {e}")

        if self.enabled:
            self._start_worker()

        if HAS_EDGE_TTS:
            logger.info("TTS: edge-tts + worker fronta")
        elif self._has_pyttsx3:
            logger.info("TTS: pyttsx3 + worker fronta")
        else:
            logger.warning("TTS: žádný engine není dostupný")

    # ── Worker ────────────────────────────────────────

    def _start_worker(self) -> None:
        self._running = True
        self._worker = threading.Thread(target=self._worker_loop,
                                        daemon=True, name="tts-worker")
        self._worker.start()

    def _worker_loop(self) -> None:
        """Jeden vlákno zpracovává frontu sériově."""
        while self._running:
            try:
                item = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if item is _STOP_SENTINEL:
                self._queue.task_done()
                break

            text = item
            try:
                self._play(text)
            except Exception as e:
                logger.error(f"TTS worker chyba: {e}")
            finally:
                self._queue.task_done()

    def _play(self, text: str) -> None:
        """Volá se z worker vlákna. Preferuje streaming pokud ffplay je dostupný."""
        if HAS_EDGE_TTS:
            if self._player == "ffplay" and self._streaming_enabled:
                asyncio.run(self._speak_edge_tts_streaming(text))
            else:
                asyncio.run(self._speak_edge_tts(text))
        elif self._has_pyttsx3:
            self._speak_pyttsx3(text)
        else:
            logger.warning("TTS není dostupný")

    # ── Veřejné API ───────────────────────────────────

    def speak(self, text: str) -> None:
        """Neblokující — přidá text do fronty pro worker."""
        if not self.enabled or not text:
            return
        self._queue.put(text)

    def speak_streaming(self, generator) -> None:
        """
        Přijme generátor chunků (z Ollama stream_ask) a přehrává věty
        okamžitě po dokončení — odezva klesá z ~5s na ~1s.
        Interpunkce: . ! ? ; a čárka před spojkami.
        """
        if not self.enabled:
            return
        import re
        _SENT_END = re.compile(
            r'(?<=[.!?;])\s+'           # po tečce/vykřičníku/otazníku/středníku
            r'|(?<=,)\s+(?=a\s|ale\s|nebo\s|takže\s|protože\s)'  # čárka před spojkou
        )
        buffer = ""
        for chunk in generator:
            buffer += chunk
            parts = _SENT_END.split(buffer)
            for sentence in parts[:-1]:
                s = sentence.strip()
                if s:
                    self.speak(s)
            buffer = parts[-1]
        if buffer.strip():
            self.speak(buffer.strip())

    def stop(self) -> None:
        """Zastaví aktuální přehrávání a vymaže frontu."""
        # Vyprázdni frontu
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                break
        # Zabit aktuální subprocess
        proc = self._current_proc
        if proc:
            try:
                proc.terminate()
            except Exception:
                pass
            self._current_proc = None

    def shutdown(self) -> None:
        """Zastaví worker vlákno při ukončení aplikace."""
        self._running = False
        self._queue.put(_STOP_SENTINEL)
        if self._worker:
            self._worker.join(timeout=3)

    def is_available(self) -> bool:
        return self.enabled and (HAS_EDGE_TTS or self._has_pyttsx3)

    # ── Interní přehrávání ────────────────────────────

    async def _speak_edge_tts_streaming(self, text: str) -> None:
        """Streamuje audio přímo do ffplay stdin — žádný dočasný soubor, nižší latence."""
        if not HAS_EDGE_TTS:
            return
        try:
            communicate = edge_tts.Communicate(text, self.voice)

            # Spusť ffplay s stdin jako vstupem
            proc = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
                 "-i", "pipe:0"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._current_proc = proc

            try:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        if proc.stdin and not proc.stdin.closed:
                            try:
                                proc.stdin.write(chunk["data"])
                            except BrokenPipeError:
                                break  # ffplay skončil

                if proc.stdin and not proc.stdin.closed:
                    proc.stdin.close()

                proc.wait(timeout=30)
            except Exception as e:
                logger.error(f"TTS streaming chyba: {e}")
                try:
                    proc.kill()
                except Exception:
                    pass
            finally:
                self._current_proc = None

        except Exception as e:
            logger.error(f"edge-tts streaming init chyba: {e}")
            # Fallback na file-based TTS
            await self._speak_edge_tts(text)

    async def _speak_edge_tts(self, text: str) -> None:
        try:
            communicate = edge_tts.Communicate(text, self.voice)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_path = f.name
            await communicate.save(temp_path)
            try:
                if os.name == "nt":
                    # cmd /c start — bez shell=True
                    proc = subprocess.Popen(
                        ["cmd", "/c", "start", "/wait", "", temp_path]
                    )
                elif self._player == "ffplay":
                    proc = subprocess.Popen(
                        ["ffplay", "-nodisp", "-autoexit",
                         "-loglevel", "quiet", temp_path])
                elif self._player:
                    proc = subprocess.Popen([self._player, "-q", temp_path])
                else:
                    logger.error("Žádný audio přehrávač")
                    return
                self._current_proc = proc
                proc.wait()
                self._current_proc = None
            finally:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"edge-tts chyba: {e}")

    def _speak_pyttsx3(self, text: str) -> None:
        try:
            if self._pyttsx3_engine:
                self._pyttsx3_engine.setProperty("rate", self.rate)
                self._pyttsx3_engine.say(text)
                self._pyttsx3_engine.runAndWait()
        except Exception as e:
            logger.error(f"pyttsx3 chyba: {e}")

    def _find_player(self) -> Optional[str]:
        for player in ("mpg123", "ffplay", "cvlc", "mplayer"):
            if subprocess.run(["which", player],
                              capture_output=True).returncode == 0:
                return player
        return None
