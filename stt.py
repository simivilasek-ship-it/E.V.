"""
JARVIS v4.4 — Speech-to-Text (STT)
Rozpoznávání řeči: Google STT primárně, Vosk offline fallback.
"""

import logging
import os
from typing import Optional

try:
    import speech_recognition as sr
    HAS_STT = True
except ImportError:
    HAS_STT = False
    sr = None

try:
    import vosk
    HAS_VOSK = True
except ImportError:
    HAS_VOSK = False

logger = logging.getLogger(__name__)


class VoskSTT:
    """Offline STT přes Vosk — funguje bez internetu, česky."""

    DEFAULT_MODEL_PATH = os.path.expanduser("~/.jarvis/vosk-model-cs")
    SMALL_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-cs-0.4-rhasspy.zip"

    def __init__(self, model_path: str = None, sample_rate: int = 16000):
        self._available = False
        self._model = None
        self._sample_rate = sample_rate

        if not HAS_VOSK:
            logger.info("VoskSTT: vosk není nainstalován (pip install vosk)")
            return

        path = model_path or self.DEFAULT_MODEL_PATH
        if not os.path.isdir(path):
            logger.info(f"VoskSTT: model nenalezen v {path}. Stáhni: download_vosk_model()")
            return

        try:
            vosk.SetLogLevel(-1)
            self._model = vosk.Model(path)
            self._available = True
            logger.info(f"VoskSTT: model načten z {path}")
        except Exception as e:
            logger.error(f"VoskSTT: chyba načítání modelu: {e}")

    @property
    def available(self) -> bool:
        return self._available

    def listen(self, timeout: float = 5.0, phrase_timeout: float = 2.0) -> str:
        """Poslouchá mikrofon a vrátí rozpoznaný text. Offline, bez internetu."""
        if not self._available:
            return ""
        try:
            import pyaudio, json, time
            rec = vosk.KaldiRecognizer(self._model, self._sample_rate)
            pa = pyaudio.PyAudio()
            stream = pa.open(format=pyaudio.paInt16, channels=1,
                             rate=self._sample_rate, input=True,
                             frames_per_buffer=8192)
            stream.start_stream()
            start = time.time()
            silence_start = None
            try:
                while time.time() - start < timeout:
                    data = stream.read(4096, exception_on_overflow=False)
                    if rec.AcceptWaveform(data):
                        text = json.loads(rec.Result()).get("text", "").strip()
                        if text:
                            return text
                    else:
                        partial = json.loads(rec.PartialResult()).get("partial", "")
                        if partial:
                            silence_start = None
                        elif silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > phrase_timeout:
                            break
            finally:
                stream.stop_stream()
                stream.close()
                pa.terminate()
            return json.loads(rec.FinalResult()).get("text", "").strip()
        except Exception as e:
            logger.error(f"VoskSTT.listen chyba: {e}")
            return ""


def download_vosk_model(model_path: str = None, url: str = None) -> str:
    """Stáhne Vosk český model (~50 MB) do ~/.jarvis/vosk-model-cs/."""
    import zipfile, io, requests
    path = model_path or VoskSTT.DEFAULT_MODEL_PATH
    url  = url or VoskSTT.SMALL_MODEL_URL
    if os.path.isdir(path):
        return f"Model již existuje: {path}"
    os.makedirs(path, exist_ok=True)
    logger.info(f"Stahuji Vosk model z {url} ...")
    try:
        r = requests.get(url, timeout=120, stream=True)
        r.raise_for_status()
        content = b"".join(r.iter_content(chunk_size=65536))
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            prefix = z.namelist()[0].split("/")[0] + "/"
            for member in z.namelist():
                if member.startswith(prefix) and not member.endswith("/"):
                    rel  = member[len(prefix):]
                    dest = os.path.join(path, rel)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with open(dest, "wb") as f:
                        f.write(z.read(member))
        return f"Model stažen: {path}"
    except Exception as e:
        import shutil
        shutil.rmtree(path, ignore_errors=True)
        return f"Chyba stahování: {e}"

class SileroVAD:
    """Voice Activity Detection přes Silero VAD model (torch).

    Výhoda oproti energy threshold: funguje v hlučném prostředí,
    neusekává začátky/konce vět. Opt-in — bez torch funguje jako no-op.
    """

    SAMPLE_RATE = 16_000
    CHUNK_MS    = 32   # ms per chunk

    def __init__(self):
        self._model    = None
        self._utils    = None
        self.available = False
        try:
            import torch
            model, utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                trust_repo=True,
            )
            self._model  = model
            self._utils  = utils
            self.available = True
            logger.info("SileroVAD: model načten")
        except Exception as e:
            logger.info(f"SileroVAD: nedostupný ({e}) — používám energy threshold")

    def is_speech(self, pcm_bytes: bytes) -> bool:
        """Vrátí True pokud chunk obsahuje řeč (confidence > 0.5)."""
        if not self.available:
            return True  # fallback — nechej projít vše
        try:
            import torch
            chunk = torch.frombuffer(pcm_bytes, dtype=torch.int16).float() / 32768.0
            conf  = self._model(chunk.unsqueeze(0), self.SAMPLE_RATE).item()
            return conf > 0.5
        except Exception:
            return True

    def listen_with_vad(self, timeout: float = 10.0, silence_after: float = 1.2) -> bytes:
        """Nahraje audio — začne při detekci řeči, skončí po tichu.

        Vrátí raw PCM bytes (int16, mono, 16kHz).
        """
        if not self.available:
            return b""
        try:
            import pyaudio, time as _t
            pa     = pyaudio.PyAudio()
            chunk  = int(self.SAMPLE_RATE * self.CHUNK_MS / 1000)
            stream = pa.open(format=pyaudio.paInt16, channels=1,
                             rate=self.SAMPLE_RATE, input=True,
                             frames_per_buffer=chunk)
            stream.start_stream()
            frames:      list[bytes] = []
            speech_start = False
            silence_ts   = None
            deadline     = _t.time() + timeout

            while _t.time() < deadline:
                data    = stream.read(chunk, exception_on_overflow=False)
                is_sp   = self.is_speech(data)

                if is_sp:
                    speech_start = True
                    silence_ts   = None
                    frames.append(data)
                elif speech_start:
                    frames.append(data)
                    if silence_ts is None:
                        silence_ts = _t.time()
                    elif _t.time() - silence_ts > silence_after:
                        break  # dostatečné ticho po řeči

            stream.stop_stream()
            stream.close()
            pa.terminate()
            return b"".join(frames)
        except Exception as e:
            logger.warning(f"SileroVAD.listen_with_vad chyba: {e}")
            return b""


class STTEngine:
    """Engine pro rozpoznávání řeči — Google primárně, Vosk offline fallback."""

    def __init__(self, config: dict):
        self.config = config
        self.recognizer = None
        self.language = config.get("stt_language", "cs-CZ")

        if HAS_STT:
            self.recognizer = sr.Recognizer()
            self.recognizer.pause_threshold = 1.0
            self.recognizer.energy_threshold = config.get("stt_energy_threshold", 300)
            self.recognizer.dynamic_energy_threshold = True
            logger.info(f"STT engine inicializován (jazyk: {self.language})")
        else:
            logger.warning("SpeechRecognition není nainstalován - STT nebude fungovat")

        # Vosk offline fallback
        self._vosk = VoskSTT(config.get("vosk_model_path"))
        if self._vosk.available:
            logger.info("STT: Vosk offline engine dostupný jako fallback")

        # Silero VAD — opt-in (vyžaduje torch)
        self._vad = SileroVAD()
        if self._vad.available:
            logger.info("STT: Silero VAD aktivní — přesná detekce řeči")

    # Jazyky podporované Google Speech Recognition
    _SUPPORTED_LANGUAGES = {
        "cs-CZ", "en-US", "en-GB", "de-DE", "fr-FR", "es-ES",
        "it-IT", "pl-PL", "sk-SK", "ru-RU", "zh-CN", "ja-JP",
        "ko-KR", "pt-BR", "nl-NL", "sv-SE", "da-DK", "fi-FI",
        "nb-NO", "hu-HU", "ro-RO", "tr-TR", "uk-UA",
    }

    def set_language(self, language: str) -> bool:
        """Nastaví jazyk rozpoznávání. Vrátí False pro nepodporovaný jazyk."""
        if language not in self._SUPPORTED_LANGUAGES:
            logger.warning(f"Nepodporovaný jazyk STT: '{language}'. "
                           f"Podporované: {sorted(self._SUPPORTED_LANGUAGES)}")
            return False
        self.language = language
        logger.info(f"Jazyk STT změněn na: {language}")
        return True

    def _listen_with_vad(self) -> Optional["sr.AudioData"]:
        """Nahraje audio přes Silero VAD a vrátí sr.AudioData pro Google/Vosk."""
        pcm = self._vad.listen_with_vad(
            timeout=self.config.get("stt_timeout", 10),
            silence_after=self.config.get("stt_silence_after", 1.2),
        )
        if not pcm:
            return None
        try:
            return sr.AudioData(pcm, sample_rate=16000, sample_width=2)
        except Exception as e:
            logger.warning(f"VAD → AudioData chyba: {e}")
            return None

    def listen(self) -> Optional[str]:
        """
        Poslouchá mikrofon a vrátí rozpoznaný text.
        Pokud je Silero VAD dostupný, používá ho místo energy threshold.
        Returns None při chybě nebo prázdném vstupu.
        """
        if not HAS_STT or not self.recognizer:
            logger.error("STT není dostupný")
            return None

        # ── Silero VAD cesta ──────────────────────────
        if self._vad.available:
            logger.info("Poslouchám (VAD)...")
            audio = self._listen_with_vad()
            if audio is None:
                return None
            try:
                text = self.recognizer.recognize_google(audio, language=self.language)
                logger.info(f"VAD rozpoznáno: {text}")
                return text
            except sr.UnknownValueError:
                if self._vosk.available:
                    text = self._vosk.listen(timeout=5.0)
                    return text if text else None
                return None
            except sr.RequestError as e:
                logger.error(f"Google STT chyba: {e}")
                if self._vosk.available:
                    return self._vosk.listen(timeout=5.0) or None
                return None

        # ── Fallback: classic energy threshold ────────
        try:
            with sr.Microphone() as source:
                logger.debug("Přizpůsobuji se okolnímu hluku...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)

                logger.info("Poslouchám...")
                audio = self.recognizer.listen(
                    source,
                    timeout=self.config.get("stt_timeout", 10),
                    phrase_time_limit=self.config.get("stt_phrase_limit", 15)
                )

            # Primární rozpoznávání (Google)
            try:
                text = self.recognizer.recognize_google(audio, language=self.language)
                logger.info(f"Rozpoznáno: {text}")
                return text
            except sr.UnknownValueError:
                logger.warning("Nerozuměl jsem - zkouším offline...")
                # Fallback na offline rozpoznávání
                try:
                    text = self.recognizer.recognize_sphinx(audio, language=self.language)
                    logger.info(f"Offline rozpoznáno: {text}")
                    return text
                except sr.UnknownValueError:
                    logger.warning("Offline rozpoznávání také selhalo")
                    return None

        except sr.WaitTimeoutError:
            logger.warning("Timeout - žádný zvuk")
            return None
        except sr.RequestError as e:
            logger.error(f"Chyba Google STT API: {e}")
            if self._vosk.available:
                logger.info("Přepínám na Vosk offline STT")
                text = self._vosk.listen(timeout=5.0)
                return text if text else None
            return None
        except Exception as e:
            logger.error(f"Chyba mikrofonu: {e}")
            return None

    def is_available(self) -> bool:
        """Vrátí True pokud STT funguje"""
        return HAS_STT and self.recognizer is not None

# ══════════════════════════════════════════════════════
#  WHISPER STT — lokální, přesný, offline
# ══════════════════════════════════════════════════════

try:
    from faster_whisper import WhisperModel as _WhisperModel
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

class WhisperSTT:
    """Lokální Whisper STT přes faster-whisper (CTranslate2).

    Přesnější než Vosk, podporuje češtinu bez speciálního modelu.
    Instalace: pip install faster-whisper
    Modely:    tiny (75 MB) | base (145 MB) | small (466 MB) | medium (1.5 GB)
    """

    MODELS = {
        "tiny":   "tiny",
        "base":   "base",
        "small":  "small",
        "medium": "medium",
    }
    DEFAULT_MODEL = "base"
    DEFAULT_LANG  = "cs"

    def __init__(self, model_size: str = None, language: str = None,
                 device: str = "cpu", compute_type: str = "int8"):
        self._model     = None
        self._available = False
        self._language  = language or self.DEFAULT_LANG

        if not HAS_WHISPER:
            logger.info("WhisperSTT: faster-whisper není nainstalován — pip install faster-whisper")
            return
        size = model_size or self.DEFAULT_MODEL
        try:
            self._model = _WhisperModel(size, device=device, compute_type=compute_type)
            self._available = True
            logger.info(f"WhisperSTT: model '{size}' načten ({device}/{compute_type})")
        except Exception as e:
            logger.error(f"WhisperSTT: chyba načítání modelu '{size}': {e}")

    @property
    def available(self) -> bool:
        return self._available

    def transcribe_file(self, audio_path: str) -> str:
        """Přepíše audio soubor (WAV/MP3/...) na text."""
        if not self._available:
            return ""
        try:
            segments, info = self._model.transcribe(
                audio_path, language=self._language, beam_size=5)
            text = " ".join(s.text.strip() for s in segments)
            logger.info(f"WhisperSTT: '{text[:80]}' (lang={info.language}, p={info.language_probability:.2f})")
            return text.strip()
        except Exception as e:
            logger.error(f"WhisperSTT.transcribe_file chyba: {e}")
            return ""

    def listen(self, timeout: float = 10.0, silence_after: float = 1.5) -> str:
        """Nahraje z mikrofonu (přes pyaudio), uloží do temp WAV a přepíše Whisperem."""
        if not self._available:
            return ""
        try:
            import pyaudio, wave, tempfile, os, time as _t
            RATE, CHUNK, CHANNELS = 16000, 1024, 1
            pa     = pyaudio.PyAudio()
            stream = pa.open(format=pyaudio.paInt16, channels=CHANNELS,
                             rate=RATE, input=True, frames_per_buffer=CHUNK)
            frames = []
            stream.start_stream()
            deadline = _t.time() + timeout
            silence_start = None
            RMS_THRESHOLD = 300

            while _t.time() < deadline:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
                import struct
                rms = (sum(v ** 2 for v in struct.unpack(f"{len(data)//2}h", data)) / (len(data)//2)) ** 0.5
                if rms > RMS_THRESHOLD:
                    silence_start = None
                else:
                    if silence_start is None:
                        silence_start = _t.time()
                    elif _t.time() - silence_start > silence_after and len(frames) > 10:
                        break

            stream.stop_stream(); stream.close(); pa.terminate()

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp = f.name
            with wave.open(tmp, "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(pa.get_sample_size(pyaudio.paInt16))
                wf.setframerate(RATE)
                wf.writeframes(b"".join(frames))

            text = self.transcribe_file(tmp)
            os.unlink(tmp)
            return text
        except Exception as e:
            logger.error(f"WhisperSTT.listen chyba: {e}")
            return ""
