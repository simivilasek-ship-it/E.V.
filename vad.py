"""Voice Activity Detection (VAD)

Provides a very small abstraction so Jarvis can do "barge-in" interruption.

- Preferred backend: webrtcvad (fast, CPU, low latency)
- Fallback: simple RMS energy threshold

Input audio is expected to be 16-bit mono PCM.
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass

try:
    import audioop  # type: ignore  # removed in Python 3.13+
except ImportError:
    audioop = None  # type: ignore

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
            rms = _pcm_rms(pcm16)
            return rms >= int(self.cfg.rms_threshold)
        except Exception:
            return False


def _pcm_rms(pcm16: bytes) -> int:
    """RMS energy for 16-bit mono PCM (audioop.rms replacement on Py 3.13+)."""
    if audioop is not None:
        return int(audioop.rms(pcm16, 2))
    if len(pcm16) < 2:
        return 0
    count = len(pcm16) // 2
    samples = struct.unpack(f"<{count}h", pcm16[: count * 2])
    if not samples:
        return 0
    mean_sq = sum(s * s for s in samples) / len(samples)
    return int(mean_sq ** 0.5)


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
