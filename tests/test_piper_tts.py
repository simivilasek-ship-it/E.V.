"""
Testy pro PiperTTS — opt-in lokální TTS engine.
Všechny scénáře jsou bez skutečného piper-tts nebo model souboru.
"""
import sys
from unittest.mock import patch, MagicMock


def test_init_no_piper():
    """Bez nainstalovaného piper-tts musí available == False."""
    # Simulujeme chybějící piper modul
    with patch.dict(sys.modules, {"piper": None}):
        from tts import PiperTTS
        p = PiperTTS()
        assert p.available is False


def test_init_no_model_file(tmp_path):
    """piper-tts nainstalován, ale model soubory chybí → available == False."""
    mock_piper_voice = MagicMock()
    mock_piper_module = MagicMock()
    mock_piper_module.PiperVoice = mock_piper_voice

    with patch.dict(sys.modules, {"piper": mock_piper_module}):
        from tts import PiperTTS
        # data_dir ukazuje na prázdný tmp_path — žádné .onnx soubory
        p = PiperTTS(data_dir=str(tmp_path))
        assert p.available is False


def test_synthesize_returns_false_unavailable(tmp_path):
    """Engine s available=False musí vrátit False ze synthesize_to_file."""
    with patch.dict(sys.modules, {"piper": None}):
        from tts import PiperTTS
        p = PiperTTS()
        assert p.available is False
        result = p.synthesize_to_file("test text", str(tmp_path / "out.wav"))
        assert result is False
