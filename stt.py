"""
JARVIS v4.2 — Speech-to-Text (STT)
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

    def set_language(self, language: str) -> bool:
        """Nastaví jazyk rozpoznávání."""
        self.language = language
        logger.info(f"Jazyk STT změněn na: {language}")
        return True

    def listen(self) -> Optional[str]:
        """
        Poslouchá mikrofon a vrátí rozpoznaný text
        Returns None při chybě nebo prázdném vstupu
        """
        if not HAS_STT or not self.recognizer:
            logger.error("STT není dostupný")
            return None

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