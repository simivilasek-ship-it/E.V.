import pytest

from vad import VAD, VADConfig

pytestmark = [pytest.mark.unit]


def test_vad_rms_detects_loud_signal():
    cfg = VADConfig(mode="rms", sample_rate=16000, rms_threshold=10)
    vad = VAD(cfg)
    # generate a fake loud frame: alternating max amplitude samples
    pcm = (b"\xff\x7f\x00\x80" * 160)  # 640 bytes
    assert vad.is_speech(pcm) is True


def test_vad_rms_silence_is_not_speech():
    cfg = VADConfig(mode="rms", sample_rate=16000, rms_threshold=100)
    vad = VAD(cfg)
    pcm = b"\x00\x00" * 320
    assert vad.is_speech(pcm) is False
