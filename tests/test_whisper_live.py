"""Unit tests for Whisper Live helpers that do not need audio hardware."""
from __future__ import annotations

import wave

import pytest

from whisper_live import VADFilter, WhisperTranscriber, pcm_to_wav

pytestmark = [pytest.mark.unit]


def test_vad_without_backend_returns_input():
    vad = VADFilter()
    vad._vad = None
    payload = b"\x00\x01" * 16
    assert vad.feed(payload) == payload
    assert vad.flush() is None


def test_vad_flush_returns_buffered_speech():
    vad = VADFilter()
    vad._speech_frames = [b"aa", b"bb"]
    assert vad.flush() == b"aabb"
    assert vad.flush() is None


def test_pcm_to_wav_roundtrip():
    pcm = b"\x00\x00\xff\x7f\x00\x80"
    wav = pcm_to_wav(pcm, sample_rate=16000)
    assert wav[:4] == b"RIFF"
    import io
    with wave.open(io.BytesIO(wav), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 16000
        assert wf.getsampwidth() == 2
        assert wf.readframes(wf.getnframes()) == pcm


def test_transcriber_backend_none_without_keys(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    import whisper_live as wl
    monkeypatch.setattr(wl, "HAS_FASTER_WHISPER", False)
    monkeypatch.setattr(wl, "HAS_OPENAI_WHISPER", False)
    t = WhisperTranscriber({"stt_language": "cs-CZ"})
    assert t._backend == "none"
    assert t.available is False


def test_transcriber_prefers_groq_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    t = WhisperTranscriber({"groq_api_key": "gsk_test"})
    assert t._backend == "groq"
    assert t.available is True
