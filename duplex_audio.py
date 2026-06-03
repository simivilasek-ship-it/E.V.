"""
duplex_audio.py

Duplex audio engine — integruje WhisperLive real-time STT + streaming TTS.
Zpětně kompatibilní interface: DuplexEngine.start/stop/send_audio_frame/synthesize_and_play.

Backend detekce (automaticky):
  1. RealDuplexEngine (whisper_live.py) — sounddevice + Whisper/Groq
  2. Fallback: původní MVP skeleton (pouze UI, bez audio)
"""
from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class DuplexEngine:
    """
    Duplex audio orchestrator.
    Deleguje na RealDuplexEngine pokud jsou dostupné závislosti,
    jinak fallback na no-op skeleton.

    Callbacks:
      on_transcript(text: str)   — voláno po každém rozpoznaném segmentu
      on_speech_start()          — začátek řeči
      on_speech_end()            — konec řeči (před transkripcí)
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        self._real: Optional[object] = None
        self._running = False
        self.on_transcript:   Optional[Callable[[str], None]] = None
        self.on_speech_start: Optional[Callable[[], None]]    = None
        self.on_speech_end:   Optional[Callable[[], None]]    = None
        self._interrupt_event = threading.Event()

        self._init_real_engine()

    def _init_real_engine(self):
        try:
            from whisper_live import RealDuplexEngine
            real = RealDuplexEngine(self.config)
            if real.available:
                self._real = real
                logger.info("DuplexEngine: RealDuplexEngine (Whisper Live) aktivní")
            else:
                logger.info("DuplexEngine: RealDuplexEngine nedostupný — používám skeleton")
        except Exception as e:
            logger.debug(f"DuplexEngine: RealDuplexEngine init selhal ({e})")

    def start(self):
        if self._running:
            return
        self._running = True

        if self._real:
            self._real.on_transcript   = self._fwd_transcript
            self._real.on_speech_start = self.on_speech_start
            self._real.on_speech_end   = self.on_speech_end
            self._real.start()
        else:
            logger.info("DuplexEngine skeleton: spuštěn (bez audio hardware)")

    def stop(self):
        self._running = False
        if self._real:
            self._real.stop()

    def interrupt(self):
        """Barge-in: přeruší aktuální TTS přehrávání."""
        self._interrupt_event.set()
        if self._real:
            try:
                self._real.interrupt()
            except Exception:
                pass

    def send_audio_frame(self, frame: bytes):
        """Přijme audio frame (např. ze WebSocket WebRTC)."""
        if self._real:
            self._real.send_audio_frame(frame)

    def synthesize_and_play(self, text: str):
        """Streaming TTS s podporou přerušení (barge-in)."""
        self._interrupt_event.clear()
        if self._real:
            try:
                self._real.synthesize_and_play(text, self._interrupt_event)
                return
            except Exception as e:
                logger.warning(f"Real TTS selhal ({e}), fallback na callback")
        # Fallback: přepošli text zpět jako transcript (původní chování)
        if self.on_transcript:
            self.on_transcript(text)

    def _fwd_transcript(self, text: str):
        if self.on_transcript:
            self.on_transcript(text)

    @property
    def backend(self) -> str:
        return "real" if self._real else "skeleton"

    @property
    def available(self) -> bool:
        return self._real is not None


# Singleton per config
_engine: Optional[DuplexEngine] = None


def get_duplex_engine(config: dict = None) -> DuplexEngine:
    global _engine
    if _engine is None:
        _engine = DuplexEngine(config or {})
    return _engine
