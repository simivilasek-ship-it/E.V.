"""ElevenLabs TTS — teplý ženský hlas Lily, model eleven_v3."""

from unittest.mock import patch

from tts import (
    ELEVENLABS_FEMALE_VOICE_ID,
    elevenlabs_configured,
    humanize_elevenlabs_text,
    infer_tts_language,
    iter_elevenlabs_audio,
)
from src.api.runtime import speak_web_reply


def test_sample_voice_id_is_not_used_as_default():
    """Dokumentační ID NOpBlnGInO9m6vDvFkFC je mužský Grandpa Spuds."""
    assert ELEVENLABS_FEMALE_VOICE_ID != "NOpBlnGInO9m6vDvFkFC"
    assert ELEVENLABS_FEMALE_VOICE_ID == "pFZP5JQG7iQjIQuC4Bku"


def test_infer_language_czech_and_english():
    assert infer_tts_language("Ahoj, kolik je hodin?") == "cs"
    assert infer_tts_language("Hello there") == "en"


def test_elevenlabs_configured_from_env(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    assert elevenlabs_configured({}) is False
    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk_test")
    assert elevenlabs_configured({}) is True
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    assert elevenlabs_configured({"elevenlabs_api_key": "sk_cfg"}) is True


def test_iter_elevenlabs_audio_posts_v3_female_voice():
    captured = {}

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=4096):
            yield b"ID3fake"

    def fake_post(url, headers=None, json=None, stream=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["stream"] = stream
        return FakeResp()

    with patch("requests.post", side_effect=fake_post):
        chunks = list(
            iter_elevenlabs_audio(
                "Ahoj",
                api_key="sk_test",
            )
        )

    assert chunks == [b"ID3fake"]
    assert captured["stream"] is True
    assert captured["headers"]["xi-api-key"] == "sk_test"
    assert captured["json"]["model_id"] == "eleven_v3"
    assert captured["json"]["language_code"] == "cs"
    assert captured["json"]["apply_text_normalization"] == "auto"
    vs = captured["json"]["voice_settings"]
    assert vs["stability"] == 0.15
    assert vs["similarity_boost"] == 0.85
    assert vs["style"] == 0.65
    assert vs["use_speaker_boost"] is True
    assert captured["json"]["text"] == "Ahoj"
    assert "/stream" not in captured["url"]
    assert "mp3_44100_192" in captured["url"]
    assert ELEVENLABS_FEMALE_VOICE_ID in captured["url"]


def test_iter_elevenlabs_retries_128kbps_after_403():
    urls = []

    class Forbidden:
        status_code = 403

        def raise_for_status(self):
            raise RuntimeError("403 Client Error: Forbidden")

        def iter_content(self, chunk_size=4096):
            yield b""

    class Ok:
        status_code = 200

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=4096):
            yield b"ID3ok"

    def fake_post(url, headers=None, json=None, stream=None, timeout=None):
        urls.append(url)
        if "mp3_44100_128" in url:
            return Ok()
        return Forbidden()

    with patch("requests.post", side_effect=fake_post):
        chunks = list(iter_elevenlabs_audio("Ahoj", api_key="sk_test"))

    assert chunks == [b"ID3ok"]
    assert any("mp3_44100_192" in u for u in urls)
    assert any("mp3_44100_128" in u for u in urls)


def test_synthesize_speech_falls_back_when_elevenlabs_fails():
    from tts import synthesize_speech

    with patch("tts.iter_elevenlabs_audio", side_effect=RuntimeError("403")), \
         patch("tts.HAS_EDGE_TTS", True), \
         patch("tts._edge_tts_bytes", return_value=b"ID3edge") as edge:
        data, mime = synthesize_speech("Ahoj", {"elevenlabs_api_key": "sk_test"})
    assert data == b"ID3edge"
    assert mime == "audio/mpeg"
    edge.assert_called_once()


def test_speak_web_reply_noop_when_runtime_not_ready():
    speak_web_reply("Ahoj")


def test_speak_web_reply_calls_runtime_speak(monkeypatch):
    spoken = []

    class FakeApp:
        def _speak(self, text):
            spoken.append(text)

    monkeypatch.setattr("src.api.runtime.is_ready", lambda: True)
    monkeypatch.setattr("src.api.runtime.get_runtime", lambda: FakeApp())
    monkeypatch.setattr("config.CONFIG", {"web_mode": False})
    speak_web_reply("Hotovo.")
    assert spoken == ["Hotovo."]


def test_humanize_elevenlabs_text_keeps_speech_alive():
    assert humanize_elevenlabs_text("Ahoj, Simi.") == "Ahoj, Simi."
    assert humanize_elevenlabs_text("[calm] Už to mám.").startswith("[calm]")
    from tts import prepare_speech_text
    assert prepare_speech_text("Ahoj **světe**") == "Ahoj světe"
    assert "def" not in prepare_speech_text("viz ```python\ndef x():\n  pass\n``` hotovo")


def test_play_prefers_elevenlabs_when_key_present():
    import tts as tts_module

    with patch.object(tts_module.TTSEngine, "_start_worker"):
        engine = tts_module.TTSEngine({
            "tts_enabled": False,
            "elevenlabs_api_key": "sk_test",
        })
    engine._elevenlabs_key = "sk_test"
    called = []
    engine._speak_elevenlabs = lambda text: called.append(text) or True
    engine._play("Otevřu Chrome.")
    assert called == ["Otevřu Chrome."]


def test_speak_streaming_elevenlabs_keeps_one_utterance():
    import tts as tts_module
    from unittest.mock import MagicMock

    with patch.object(tts_module.TTSEngine, "_start_worker"):
        engine = tts_module.TTSEngine({
            "tts_enabled": False,
            "elevenlabs_api_key": "sk_test",
        })
    engine.enabled = True
    engine._elevenlabs_key = "sk_test"
    engine.speak = MagicMock()
    engine.speak_streaming(iter(["První věta. ", "Druhá věta."]))
    engine.speak.assert_called_once()
    assert "První" in engine.speak.call_args[0][0]
    assert "Druhá" in engine.speak.call_args[0][0]


def test_espeak_synthesize_wav_when_installed(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    from tts import espeak_available, _espeak_wav_bytes

    if not espeak_available():
        return
    data = _espeak_wav_bytes("Ahoj")
    assert len(data) > 44
