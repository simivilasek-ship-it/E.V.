"""Unit tests for DuplexEngine skeleton fallback (no audio hardware)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import duplex_audio

pytestmark = [pytest.mark.unit]


@pytest.fixture(autouse=True)
def reset_engine():
    duplex_audio._engine = None
    yield
    duplex_audio._engine = None


def test_skeleton_when_real_engine_missing():
    with patch.object(duplex_audio.DuplexEngine, "_init_real_engine", lambda self: None):
        eng = duplex_audio.DuplexEngine({})
    assert eng.backend == "skeleton"
    assert eng.available is False
    eng.start()
    eng.start()
    eng.send_audio_frame(b"\x00\x00")
    received = []
    eng.on_transcript = received.append
    eng.synthesize_and_play("ahoj")
    assert received == ["ahoj"]
    eng.interrupt()
    eng.stop()
    assert eng._running is False


def test_forwards_to_real_backend():
    real = MagicMock()
    with patch.object(duplex_audio.DuplexEngine, "_init_real_engine", lambda self: setattr(self, "_real", real)):
        eng = duplex_audio.DuplexEngine({})
    eng.on_transcript = MagicMock()
    eng.start()
    real.start.assert_called_once()
    eng.send_audio_frame(b"abc")
    real.send_audio_frame.assert_called_once_with(b"abc")
    eng.synthesize_and_play("hi")
    real.synthesize_and_play.assert_called_once()
    eng.stop()
    real.stop.assert_called_once()
    assert eng.backend == "real"


def test_get_duplex_engine_singleton():
    with patch.object(duplex_audio.DuplexEngine, "_init_real_engine", lambda self: None):
        a = duplex_audio.get_duplex_engine({})
        b = duplex_audio.get_duplex_engine({"x": 1})
    assert a is b
