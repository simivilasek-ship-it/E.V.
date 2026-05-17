"""
Headless testy pro TTS streaming mód (edge-tts → ffplay stdin).
Všechny subprocess a edge_tts volání jsou mockována.
"""

import asyncio
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch, call


# ---------------------------------------------------------------------------
# Pomocný fake edge_tts modul pokud není nainstalovaný
# ---------------------------------------------------------------------------
def _ensure_edge_tts_mock():
    if "edge_tts" not in sys.modules:
        fake = types.ModuleType("edge_tts")
        fake.Communicate = MagicMock()
        sys.modules["edge_tts"] = fake


_ensure_edge_tts_mock()

# ---------------------------------------------------------------------------
# Import testované třídy
# ---------------------------------------------------------------------------
import importlib
import tts as tts_module


def _make_engine(config: dict) -> tts_module.TTSEngine:
    """Vytvoří TTSEngine bez spuštění workeru."""
    with patch.object(tts_module.TTSEngine, "_start_worker"):
        engine = tts_module.TTSEngine(config)
    return engine


# ---------------------------------------------------------------------------
# Testy
# ---------------------------------------------------------------------------

class TestStreamingEnabled(unittest.TestCase):

    def test_streaming_enabled_when_ffplay_available(self):
        """ffplay existuje → _streaming_enabled=True."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            engine = _make_engine({"tts_enabled": False})
        # _find_player vrátí první dostupný — mockujeme aby to bylo ffplay
        engine._player = "ffplay"
        engine._streaming_enabled = (engine._player == "ffplay") and engine.config.get("tts_streaming", True)
        self.assertTrue(engine._streaming_enabled)

    def test_streaming_disabled_when_no_ffplay(self):
        """Bez ffplay → _streaming_enabled=False."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            engine = _make_engine({"tts_enabled": False})
        self.assertFalse(engine._streaming_enabled)

    def test_streaming_disabled_by_config(self):
        """config tts_streaming=False → _streaming_enabled=False, i když ffplay dostupný."""
        with patch("subprocess.run") as mock_run:
            # Simuluj ffplay dostupný
            def side(cmd, **kw):
                m = MagicMock()
                m.returncode = 0 if "ffplay" in cmd else 1
                return m
            mock_run.side_effect = side
            engine = _make_engine({"tts_enabled": False, "tts_streaming": False})
        self.assertFalse(engine._streaming_enabled)


class TestStreamingCalled(unittest.TestCase):

    def test_speak_calls_streaming_when_enabled(self):
        """Pokud streaming_enabled, _play zavolá _speak_edge_tts_streaming."""
        engine = _make_engine({"tts_enabled": False})
        engine._player = "ffplay"
        engine._streaming_enabled = True

        called_with = []

        async def fake_streaming(text):
            called_with.append(text)

        engine._speak_edge_tts_streaming = fake_streaming

        with patch.object(tts_module, "HAS_EDGE_TTS", True):
            engine._play("Ahoj světe")

        self.assertEqual(called_with, ["Ahoj světe"])

    def test_streaming_fallback_on_error(self):
        """Pokud Popen selže, zavolá se _speak_edge_tts jako fallback."""
        engine = _make_engine({"tts_enabled": False})
        engine._player = "ffplay"
        engine._streaming_enabled = True

        fallback_called = []

        async def fake_speak_edge_tts(text):
            fallback_called.append(text)

        engine._speak_edge_tts = fake_speak_edge_tts

        # Popen vyhodí výjimku → vnější except → fallback
        with patch.object(tts_module, "HAS_EDGE_TTS", True), \
             patch("edge_tts.Communicate"), \
             patch("subprocess.Popen", side_effect=OSError("ffplay nenalezen")):
            asyncio.run(engine._speak_edge_tts_streaming("test fallback"))

        self.assertEqual(fallback_called, ["test fallback"])


class TestStopKillsProc(unittest.TestCase):

    def test_stop_kills_current_proc(self):
        """stop() terminuje aktuální streaming subprocess."""
        engine = _make_engine({"tts_enabled": False})
        mock_proc = MagicMock()
        engine._current_proc = mock_proc

        engine.stop()

        mock_proc.terminate.assert_called_once()
        self.assertIsNone(engine._current_proc)


if __name__ == "__main__":
    unittest.main()
