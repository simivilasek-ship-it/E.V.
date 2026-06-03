"""
JARVIS — Whisper Live: Real-time duplex audio
Nahrazuje staré blocking STT (Google/Vosk) kontinuálním streamingem.

Architektura:
  Mikrofon → VAD (WebRTC) → chunky → Whisper (lokální nebo Groq Whisper API)
         ↓
  Transkript → LLM → TTS (Edge-TTS streaming)
         ↓
  Audio playback (přerušitelný)

Módy:
  1. Groq Whisper API (nejrychlejší, ~200ms, vyžaduje GROQ_API_KEY)
  2. faster-whisper lokálně (dobrý poměr rychlost/soukromí)
  3. OpenAI Whisper lokálně (pomalejší, ale funguje offline)
  4. Fallback: původní Google STT (blocking)

Použití:
  from whisper_live import WhisperLiveEngine
  engine = WhisperLiveEngine(config, on_transcript=callback)
  engine.start()
  engine.stop()
"""
from __future__ import annotations

import io
import logging
import os
import queue
import threading
import time
import wave
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# ── Detekce dostupných backendů ───────────────────────────────────────────────

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

try:
    import webrtcvad
    HAS_WEBRTCVAD = True
except ImportError:
    HAS_WEBRTCVAD = False

try:
    from faster_whisper import WhisperModel as FasterWhisperModel
    HAS_FASTER_WHISPER = True
except ImportError:
    HAS_FASTER_WHISPER = False

try:
    import whisper as _openai_whisper
    HAS_OPENAI_WHISPER = True
except ImportError:
    HAS_OPENAI_WHISPER = False


# ── VAD (Voice Activity Detection) ───────────────────────────────────────────

class VADFilter:
    """
    Detekuje úseky řeči v audio streamu.
    Vrátí kompletní utterance (od začátku řeči do konce ticha).
    """

    SAMPLE_RATE = 16000
    FRAME_MS    = 30       # webrtcvad vyžaduje 10/20/30ms
    SILENCE_FRAMES = 30    # 30 × 30ms = 0.9s ticha = konec utterance

    def __init__(self, aggressiveness: int = 2):
        self._vad = None
        if HAS_WEBRTCVAD:
            self._vad = webrtcvad.Vad(aggressiveness)
        self._frame_size = int(self.SAMPLE_RATE * self.FRAME_MS / 1000)
        self._buffer: list = []
        self._speech_frames: list = []
        self._silence_count = 0
        self._in_speech = False

    def feed(self, pcm_bytes: bytes) -> Optional[bytes]:
        """
        Přijme surová PCM data (int16, mono, 16kHz).
        Vrátí kompletní utterance bytes nebo None pokud ještě probíhá.
        """
        if not self._vad or not HAS_NUMPY:
            return pcm_bytes  # bez VAD: vracíme vše

        frame_bytes = self._frame_size * 2  # int16 = 2 bytes

        # Přidej do bufferu
        self._buffer.extend(pcm_bytes)

        result = None
        while len(self._buffer) >= frame_bytes:
            frame = bytes(self._buffer[:frame_bytes])
            self._buffer = self._buffer[frame_bytes:]

            try:
                is_speech = self._vad.is_speech(frame, self.SAMPLE_RATE)
            except Exception:
                is_speech = True

            if is_speech:
                self._in_speech = True
                self._silence_count = 0
                self._speech_frames.append(frame)
            elif self._in_speech:
                self._silence_count += 1
                self._speech_frames.append(frame)
                if self._silence_count >= self.SILENCE_FRAMES:
                    # Konec utterance
                    result = b"".join(self._speech_frames)
                    self._speech_frames = []
                    self._silence_count = 0
                    self._in_speech = False

        return result

    def flush(self) -> Optional[bytes]:
        """Vrátí zbývající řeč (při ukončení)."""
        if self._speech_frames:
            result = b"".join(self._speech_frames)
            self._speech_frames = []
            self._in_speech = False
            return result
        return None


# ── Whisper transkripce ───────────────────────────────────────────────────────

class WhisperTranscriber:
    """Abstraktní transkriptor. Vybere nejlepší dostupný backend."""

    def __init__(self, config: dict):
        self.config      = config
        self._groq_key   = config.get("groq_api_key") or os.getenv("GROQ_API_KEY", "")
        self._language   = config.get("stt_language", "cs-CZ").replace("-", "_").split("_")[0]
        self._fw_model   = None
        self._ow_model   = None
        self._backend    = self._detect_backend()
        logger.info(f"WhisperTranscriber backend: {self._backend}")

    def _detect_backend(self) -> str:
        if self._groq_key:
            return "groq"
        if HAS_FASTER_WHISPER:
            return "faster_whisper"
        if HAS_OPENAI_WHISPER:
            return "openai_whisper"
        return "none"

    def _init_faster_whisper(self):
        if self._fw_model:
            return
        try:
            model_size = self.config.get("whisper_model_size", "base")
            device = "cuda" if self.config.get("vision_gpu_enabled") else "cpu"
            compute = "float16" if device == "cuda" else "int8"
            self._fw_model = FasterWhisperModel(model_size, device=device,
                                                 compute_type=compute)
            logger.info(f"faster-whisper model={model_size} device={device}")
        except Exception as e:
            logger.error(f"faster-whisper init selhal: {e}")

    def _init_openai_whisper(self):
        if self._ow_model:
            return
        try:
            model_size = self.config.get("whisper_model_size", "base")
            self._ow_model = _openai_whisper.load_model(model_size)
            logger.info(f"openai-whisper model={model_size}")
        except Exception as e:
            logger.error(f"openai-whisper init selhal: {e}")

    def transcribe(self, audio_bytes: bytes) -> str:
        """Přepíše audio bytes na text. audio_bytes = WAV format."""
        if self._backend == "groq":
            return self._transcribe_groq(audio_bytes)
        elif self._backend == "faster_whisper":
            return self._transcribe_faster_whisper(audio_bytes)
        elif self._backend == "openai_whisper":
            return self._transcribe_openai_whisper(audio_bytes)
        return ""

    def _transcribe_groq(self, wav_bytes: bytes) -> str:
        """Groq Whisper API — nejrychlejší (~200ms)."""
        try:
            import requests
            files  = {"file": ("audio.wav", wav_bytes, "audio/wav")}
            data   = {"model": "whisper-large-v3", "language": self._language,
                      "response_format": "text"}
            headers = {"Authorization": f"Bearer {self._groq_key}"}
            r = requests.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                files=files, data=data, headers=headers, timeout=15,
            )
            r.raise_for_status()
            text = r.text.strip() if r.headers.get("content-type", "").startswith("text") else r.json().get("text", "").strip()
            logger.debug(f"Groq Whisper: {text[:80]!r}")
            return text
        except Exception as e:
            logger.warning(f"Groq Whisper selhal ({e}), zkouším lokální whisper")
            if HAS_FASTER_WHISPER:
                self._backend = "faster_whisper"
                return self._transcribe_faster_whisper(wav_bytes)
            return ""

    def _transcribe_faster_whisper(self, wav_bytes: bytes) -> str:
        self._init_faster_whisper()
        if not self._fw_model:
            return ""
        try:
            audio_io = io.BytesIO(wav_bytes)
            segments, _ = self._fw_model.transcribe(
                audio_io, language=self._language, beam_size=5,
                vad_filter=True,
            )
            return " ".join(seg.text for seg in segments).strip()
        except Exception as e:
            logger.error(f"faster-whisper transkripce selhal: {e}")
            return ""

    def _transcribe_openai_whisper(self, wav_bytes: bytes) -> str:
        self._init_openai_whisper()
        if not self._ow_model:
            return ""
        try:
            if not HAS_NUMPY:
                return ""
            audio_io = io.BytesIO(wav_bytes)
            with wave.open(audio_io, "rb") as wf:
                frames = wf.readframes(wf.getnframes())
            audio_np = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            result = self._ow_model.transcribe(audio_np, language=self._language)
            return result.get("text", "").strip()
        except Exception as e:
            logger.error(f"openai-whisper transkripce selhal: {e}")
            return ""

    @property
    def available(self) -> bool:
        return self._backend != "none"


# ── PCM → WAV helper ──────────────────────────────────────────────────────────

def pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 16000, channels: int = 1) -> bytes:
    """Převede raw int16 PCM na WAV formát (in-memory)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # int16 = 2 bytes
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


# ── Hlavní WhisperLiveEngine ──────────────────────────────────────────────────

class WhisperLiveEngine:
    """
    Kontinuální real-time STT engine.
    Zachycuje mikrofon → VAD → Whisper → callback on_transcript.

    Podporuje přerušení uprostřed věty (barge-in):
      engine.interrupt()  # přeruší aktuální TTS a začne naslouchat

    Konfigurace:
      whisper_model_size: tiny | base | small | medium (default: base)
      stt_language: cs-CZ (default)
      groq_api_key: pro Groq Whisper API
    """

    SAMPLE_RATE  = 16000
    CHANNELS     = 1
    DTYPE        = "int16"
    BLOCK_MS     = 30       # ms per audio block

    def __init__(self, config: dict = None,
                 on_transcript: Callable[[str], None] = None,
                 on_speech_start: Callable[[], None] = None,
                 on_speech_end: Callable[[], None] = None):
        if config is None:
            try:
                from config import CONFIG
                config = CONFIG
            except Exception:
                config = {}
        self.config          = config
        self._on_transcript  = on_transcript or (lambda t: logger.info(f"Transcript: {t}"))
        self._on_speech_start = on_speech_start
        self._on_speech_end   = on_speech_end
        self._running         = False
        self._interrupted     = threading.Event()
        self._audio_q: queue.Queue = queue.Queue(maxsize=200)
        self._transcribe_q: queue.Queue = queue.Queue(maxsize=50)
        self._vad             = VADFilter(aggressiveness=2)
        self._transcriber     = WhisperTranscriber(config)
        self._capture_thread: Optional[threading.Thread] = None
        self._process_thread: Optional[threading.Thread] = None

    @property
    def available(self) -> bool:
        return HAS_SOUNDDEVICE and self._transcriber.available

    def start(self):
        """Spustí real-time zachytávání a transkripci."""
        if not HAS_SOUNDDEVICE:
            logger.warning("WhisperLive: sounddevice není nainstalováno (pip install sounddevice)")
            return
        if not self._transcriber.available:
            logger.warning("WhisperLive: žádný transkripční backend není dostupný")
            return
        if self._running:
            return

        self._running = True
        self._capture_thread = threading.Thread(
            target=self._capture_loop, daemon=True, name="WhisperLive-Capture")
        self._process_thread = threading.Thread(
            target=self._process_loop, daemon=True, name="WhisperLive-Process")
        self._capture_thread.start()
        self._process_thread.start()
        logger.info(f"WhisperLive spuštěn (backend={self._transcriber._backend})")

    def stop(self):
        self._running = False
        if self._capture_thread:
            self._capture_thread.join(timeout=2.0)
        if self._process_thread:
            self._process_thread.join(timeout=2.0)
        logger.info("WhisperLive zastaven")

    def interrupt(self):
        """Přeruší aktuální TTS přehrávání (barge-in)."""
        self._interrupted.set()
        logger.info("WhisperLive: barge-in signál")

    def _capture_loop(self):
        """Zachycuje mikrofon a posílá PCM bloky do fronty."""
        block_size = int(self.SAMPLE_RATE * self.BLOCK_MS / 1000)
        try:
            with sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=self.CHANNELS,
                dtype=self.DTYPE,
                blocksize=block_size,
                callback=self._audio_callback,
            ):
                while self._running:
                    time.sleep(0.05)
        except Exception as e:
            logger.error(f"WhisperLive capture chyba: {e}")

    def _audio_callback(self, indata, frames, time_info, status):
        """Voláno sounddevice pro každý blok."""
        if status:
            logger.debug(f"Audio status: {status}")
        try:
            self._audio_q.put_nowait(indata.tobytes())
        except queue.Full:
            pass  # zahazuj pokud fronty přetékají

    def _process_loop(self):
        """Zpracovává VAD a spouští transkripci."""
        while self._running:
            # Načítej bloky z fronty
            pcm_chunks = []
            try:
                chunk = self._audio_q.get(timeout=0.1)
                pcm_chunks.append(chunk)
                # Načti více bloků pokud jsou dostupné
                while not self._audio_q.empty():
                    pcm_chunks.append(self._audio_q.get_nowait())
            except queue.Empty:
                # Zkontroluj flush při tichu
                flushed = self._vad.flush()
                if flushed and len(flushed) > self.SAMPLE_RATE * 0.3 * 2:
                    self._transcribe(flushed)
                continue

            # Agreguj a podej VAD
            pcm_all = b"".join(pcm_chunks)
            utterance = self._vad.feed(pcm_all)

            if utterance and len(utterance) > self.SAMPLE_RATE * 0.5 * 2:
                # Minimálně 0.5s řeči
                if self._on_speech_end:
                    try:
                        self._on_speech_end()
                    except Exception:
                        pass
                self._transcribe(utterance)
            elif self._vad._in_speech and self._on_speech_start:
                try:
                    self._on_speech_start()
                except Exception:
                    pass

    def _transcribe(self, pcm_bytes: bytes):
        """Spustí transkripci v separátním threadu."""
        def _run():
            try:
                wav = pcm_to_wav(pcm_bytes)
                t0  = time.monotonic()
                text = self._transcriber.transcribe(wav)
                ms   = (time.monotonic() - t0) * 1000
                if text and len(text.strip()) > 1:
                    logger.info(f"Transcript ({ms:.0f}ms): {text!r}")
                    self._on_transcript(text.strip())
            except Exception as e:
                logger.error(f"Transkripce chyba: {e}")

        t = threading.Thread(target=_run, daemon=True)
        t.start()


# ── Upgrade duplex_audio.py ───────────────────────────────────────────────────

class RealDuplexEngine:
    """
    Plnohodnotný duplex engine: STT + TTS s podporou barge-in.

    Integrace s existujícím DuplexEngine interfacem:
      engine = RealDuplexEngine(config)
      engine.on_transcript = lambda text: ...  # callback pro text
      engine.start()
    """

    def __init__(self, config: dict = None):
        if config is None:
            try:
                from config import CONFIG
                config = CONFIG
            except Exception:
                config = {}
        self.config = config
        self._whisper: Optional[WhisperLiveEngine] = None
        self._running = False
        self.on_transcript: Optional[Callable[[str], None]] = None
        self.on_speech_start: Optional[Callable[[], None]] = None
        self.on_speech_end: Optional[Callable[[], None]] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._whisper = WhisperLiveEngine(
            config=self.config,
            on_transcript=self._handle_transcript,
            on_speech_start=self.on_speech_start,
            on_speech_end=self.on_speech_end,
        )
        self._whisper.start()

    def stop(self):
        self._running = False
        if self._whisper:
            self._whisper.stop()

    def interrupt(self):
        """Barge-in: přeruší aktuální TTS."""
        if self._whisper:
            self._whisper.interrupt()

    def _handle_transcript(self, text: str):
        if self.on_transcript:
            self.on_transcript(text)

    def send_audio_frame(self, frame: bytes):
        """Přijme audio frame ze WebSocket (WebRTC)."""
        if self._whisper:
            try:
                self._whisper._audio_q.put_nowait(frame)
            except Exception:
                pass

    def synthesize_and_play(self, text: str, interrupt_event: threading.Event = None):
        """
        Streaming TTS s přerušením (edge-tts nebo pyttsx3).
        Přeruší se pokud uživatel začne mluvit (barge-in).
        """
        try:
            self._tts_streaming(text, interrupt_event)
        except Exception as e:
            logger.error(f"TTS chyba: {e}")

    def _tts_streaming(self, text: str, interrupt_event=None):
        """Edge-TTS streaming s přerušením."""
        try:
            import edge_tts
            import asyncio
            import tempfile

            voice = self.config.get("tts_voice", "cs-CZ-AntoninNeural")

            async def _speak() -> bytes:
                communicate = edge_tts.Communicate(text, voice)
                buf = io.BytesIO()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        if interrupt_event and interrupt_event.is_set():
                            logger.info("TTS přerušen (barge-in)")
                            return b""
                        buf.write(chunk["data"])
                return buf.getvalue()

            loop = asyncio.new_event_loop()
            audio_data = loop.run_until_complete(_speak())
            loop.close()

            if not audio_data:
                return

            # Přehraj přes sounddevice
            import soundfile as sf
            audio_io = io.BytesIO(audio_data)
            data, samplerate = sf.read(audio_io)
            sd.play(data, samplerate)
            sd.wait()

        except Exception as e:
            logger.warning(f"edge-tts selhal ({e}), zkouším pyttsx3")
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty("rate", self.config.get("tts_rate", 170))
                engine.say(text)
                engine.runAndWait()
            except Exception as e2:
                logger.error(f"TTS fallback selhal: {e2}")

    @property
    def available(self) -> bool:
        return HAS_SOUNDDEVICE


# Singleton
_real_duplex: Optional[RealDuplexEngine] = None


def get_real_duplex_engine(config: dict = None) -> RealDuplexEngine:
    global _real_duplex
    if _real_duplex is None:
        _real_duplex = RealDuplexEngine(config)
    return _real_duplex
