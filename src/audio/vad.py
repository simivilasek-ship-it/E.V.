"""Voice Activity Detection (VAD)

Provides a very small abstraction so Jarvis can do "barge-in" interruption.

- Preferred backend: webrtcvad (fast, CPU, low latency)
- Fallback: simple RMS energy threshold

Input audio is expected to be 16-bit mono PCM.
"""

from __future__ import annotations

import audioop
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class VADConfig:
    sample_rate: int = 16000
    frame_ms: int = 30
    mode: str = "auto"  # auto|webrtcvad|rms
    rms_threshold: int = 300
    webrtcvad_aggressiveness: int = 2  # 0..3


class VAD:
    def __init__(self, cfg: VADConfig):
        self.cfg = cfg
        self._webrtcvad = None
        self._has_webrtcvad = False

        if cfg.mode in ("auto", "webrtcvad"):
            try:
                import webrtcvad  # type: ignore

                self._webrtcvad = webrtcvad.Vad(int(cfg.webrtcvad_aggressiveness))
                self._has_webrtcvad = True
                logger.info("VAD: webrtcvad enabled")
            except Exception:
                self._webrtcvad = None
                self._has_webrtcvad = False

        if cfg.mode == "webrtcvad" and not self._has_webrtcvad:
            logger.warning("VAD: webrtcvad requested but not available; falling back to RMS")

    def is_speech(self, pcm16: bytes) -> bool:
        """Return True if speech is detected in the given frame."""
        if not pcm16:
            return False

        # webrtcvad needs specific frame sizes
        if self._has_webrtcvad and self._webrtcvad is not None:
            try:
                # valid frame lengths: 10/20/30ms
                return bool(self._webrtcvad.is_speech(pcm16, self.cfg.sample_rate))
            except Exception:
                pass

        # RMS fallback
        try:
            rms = audioop.rms(pcm16, 2)  # width=2 bytes
            return rms >= int(self.cfg.rms_threshold)
        except Exception:
            return False


_vad_singleton: VAD | None = None


def get_vad(config: dict | None = None) -> VAD:
    global _vad_singleton
    if _vad_singleton is None:
        cfg = VADConfig(
            sample_rate=int((config or {}).get("vad_sample_rate", 16000)),
            mode=str((config or {}).get("vad_mode", "auto")),
        )
        _vad_singleton = VAD(cfg)
    return _vad_singleton
