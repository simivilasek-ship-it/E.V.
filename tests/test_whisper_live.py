"""Unit tests for Whisper Live helpers that do not need audio hardware."""
from __future__ import annotations

import wave

import pytest

from whisper_live import VADFilter, WhisperTranscriber, pcm_to_wav

pytestmark = [pytest.mark.unit]


def test_energy_vad_ignores_silence():
    vad = VADFilter()
    vad._vad = None
    silence = b"\x00\x00" * vad._frame_size
    assert vad.feed(silence) is None
    assert vad.flush() is None


def test_energy_vad_emits_after_speech_and_silence():
    import struct

    vad = VADFilter()
    vad._vad = None
    amp = 9000
    speech = b"".join(
        struct.pack("<h", amp if i % 2 == 0 else -amp) for i in range(vad._frame_size)
    )
    silence = b"\x00\x00" * vad._frame_size
    assert vad.feed(speech * 8) is None
    out = vad.feed(silence * vad.SILENCE_FRAMES)
    assert out is not None
    assert len(out) >= len(speech) * vad.MIN_SPEECH_FRAMES


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
    monkeypatch.setattr(wl, "HAS_SPEECH_RECOGNITION", False)
    t = WhisperTranscriber({"stt_language": "cs-CZ"})
    assert t._backend == "none"
    assert t.available is False


def test_transcriber_uses_google_without_whisper(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    import whisper_live as wl
    monkeypatch.setattr(wl, "HAS_FASTER_WHISPER", False)
    monkeypatch.setattr(wl, "HAS_OPENAI_WHISPER", False)
    monkeypatch.setattr(wl, "HAS_SPEECH_RECOGNITION", True)
    t = WhisperTranscriber({"stt_language": "cs-CZ"})
    assert t._backend == "google"
    assert t.available is True


def test_transcriber_prefers_groq_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    t = WhisperTranscriber({"groq_api_key": "gsk_test"})
    assert t._backend == "groq"
    assert t.available is True


def test_looks_like_echo_of_greeting():
    from whisper_live import looks_like_echo

    spoken = "Čau Simi. Dobrý večer. Jsem tady."
    assert looks_like_echo("Čau Simi dobrý večer jsem tady", spoken)
    assert looks_like_echo("cau simi. dobry vecer", spoken)
    assert not looks_like_echo("kolik je hodin", spoken)
    assert not looks_like_echo("ahoj", spoken)
