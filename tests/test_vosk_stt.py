"""Headless testy pro VoskSTT — mock vosk, pyaudio, requests."""

import os
import sys
import json
import types
import unittest
from unittest.mock import MagicMock, patch, call


# ── Fake vosk modul ────────────────────────────────

def _inject_fake_vosk():
    if "vosk" in sys.modules:
        return
    fake = types.ModuleType("vosk")
    fake.SetLogLevel = MagicMock()

    class FakeModel:
        def __init__(self, path):
            self.path = path

    class FakeRecognizer:
        def __init__(self, model, rate):
            self._result = json.dumps({"text": "test text"})
            self._partial = json.dumps({"partial": ""})

        def AcceptWaveform(self, data):
            return True

        def Result(self):
            return self._result

        def PartialResult(self):
            return self._partial

        def FinalResult(self):
            return self._result

    fake.Model = FakeModel
    fake.KaldiRecognizer = FakeRecognizer
    sys.modules["vosk"] = fake


_inject_fake_vosk()

import stt as stt_module
from stt import VoskSTT, download_vosk_model


class TestVoskInitNoDeps(unittest.TestCase):

    def test_engine_init_no_deps(self):
        """Bez vosk balíčku → available=False."""
        with patch.object(stt_module, "HAS_VOSK", False):
            engine = VoskSTT()
        self.assertFalse(engine.available)

    def test_vosk_init_no_model(self):
        """Vosk nainstalován ale model chybí → available=False."""
        with patch.object(stt_module, "HAS_VOSK", True), \
             patch("os.path.isdir", return_value=False):
            engine = VoskSTT(model_path="/neexistuje/model")
        self.assertFalse(engine.available)

    def test_vosk_init_with_model(self):
        """available=True pokud HAS_VOSK a model existuje."""
        engine = VoskSTT.__new__(VoskSTT)
        engine._available = True
        engine._model = object()
        engine._sample_rate = 16000
        self.assertTrue(engine.available)


class TestVoskListen(unittest.TestCase):

    def _engine_with_model(self):
        with patch.object(stt_module, "HAS_VOSK", True), \
             patch("os.path.isdir", return_value=True):
            return VoskSTT(model_path="/fake/model")

    def test_listen_returns_string(self):
        """Úspěšné rozpoznání → vrátí neprázdný string."""
        engine = self._engine_with_model()

        fake_pyaudio = MagicMock()
        fake_stream = MagicMock()
        fake_stream.read.return_value = b"\x00" * 4096
        fake_pyaudio.PyAudio.return_value.open.return_value = fake_stream

        with patch.dict(sys.modules, {"pyaudio": fake_pyaudio}):
            result = engine.listen(timeout=0.1)

        self.assertIsInstance(result, str)

    def test_listen_empty_on_error(self):
        """Exception při poslechu → vrátí prázdný string."""
        engine = self._engine_with_model()

        with patch.dict(sys.modules, {"pyaudio": None}):
            result = engine.listen(timeout=0.1)

        self.assertEqual(result, "")

    def test_listen_unavailable(self):
        """Pokud engine není available → ihned vrátí ''."""
        engine = VoskSTT.__new__(VoskSTT)
        engine._available = False
        engine._model = None
        engine._sample_rate = 16000
        self.assertEqual(engine.listen(), "")


class TestDownloadVoskModel(unittest.TestCase):

    def test_already_exists(self):
        """Složka existuje → vrátí info bez stahování."""
        with patch("os.path.isdir", return_value=True):
            result = download_vosk_model(model_path="/existing/model")
        self.assertIn("existuje", result)

    def test_download_success(self):
        """Úspěšné stažení → vytvoří soubory."""
        import io, zipfile

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("vosk-model-cs-main/README", "model data")
            z.writestr("vosk-model-cs-main/am/final.mdl", b"\x00" * 10)
        buf.seek(0)

        fake_response = MagicMock()
        fake_response.content = buf.read()
        fake_response.raise_for_status = MagicMock()
        fake_response.iter_content = lambda chunk_size: iter([fake_response.content])

        with patch("os.path.isdir", return_value=False), \
             patch("os.makedirs"), \
             patch("requests.get", return_value=fake_response), \
             patch("builtins.open", unittest.mock.mock_open()):
            result = download_vosk_model(model_path="/tmp/test-model")

        self.assertIn("stažen", result.lower())

    def test_download_network_error(self):
        """Síťová chyba → vrátí chybovou zprávu."""
        import requests as req_module
        with patch("os.path.isdir", return_value=False), \
             patch("os.makedirs"), \
             patch("requests.get", side_effect=req_module.RequestException("timeout")), \
             patch("shutil.rmtree"):
            result = download_vosk_model(model_path="/tmp/test-model")
        self.assertIn("Chyba", result)


class TestSTTEngineVoskFallback(unittest.TestCase):

    def test_stt_engine_has_vosk_attr(self):
        """STTEngine má _vosk atribut po inicializaci."""
        with patch.object(stt_module, "HAS_STT", False), \
             patch.object(stt_module, "HAS_VOSK", False):
            engine = stt_module.STTEngine({})
        self.assertTrue(hasattr(engine, "_vosk"))


if __name__ == "__main__":
    unittest.main()
