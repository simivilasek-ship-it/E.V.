"""
vision_pipeline.py

Helper utilities for Vision pipeline:
- GPU detection
- OCR with caching
- LLaVA call wrapper with fallback and device control
"""
from __future__ import annotations
import hashlib
import os
import json
import time
from pathlib import Path
from typing import Optional

CACHE_DIR = Path.home() / ".jarvis" / "vision_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _file_hash(path: str) -> str:
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def detect_gpu() -> bool:
    """Best-effort detect CUDA/GPU availability (MVP)."""
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        # try nvidia-smi
        try:
            import subprocess
            r = subprocess.run(['nvidia-smi'], capture_output=True, timeout=1)
            return r.returncode == 0
        except Exception:
            return False


def ocr_with_cache(image_path: str, force: bool = False, langs: str = 'ces+eng') -> str:
    """Run pytesseract OCR with file-hash based cache. Returns text.
    If pytesseract not available, returns informative string.
    """
    try:
        import pytesseract
        from PIL import Image
    except Exception:
        return "pytesseract není nainstalován"

    h = _file_hash(image_path)
    cache_file = CACHE_DIR / (h + '.json')
    if cache_file.exists() and not force:
        try:
            data = json.loads(cache_file.read_text(encoding='utf-8'))
            # check TTL (1 day)
            if time.time() - data.get('ts', 0) < 24*3600:
                return data.get('text', '')
        except Exception:
            pass

    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang=langs)
        try:
            cache_file.write_text(json.dumps({'ts': time.time(), 'text': text}, ensure_ascii=False), encoding='utf-8')
        except Exception:
            pass
        return text
    except Exception as e:
        return f'OCR chyba: {e}'


def describe_with_llava(image_path: str, prompt: str, model: str = 'llava:7b', use_gpu: Optional[bool] = None) -> str:
    """Wrapper over llm.ask_vision with best-effort device control.
    If GPU not available or configured off, call normally. Returns model output or error string.
    """
    try:
        from config import CONFIG
        from llm import ask_vision
    except Exception as e:
        return f"Vision model nedostupný: {e}"

    # decide on gpu
    if use_gpu is None:
        use_gpu = bool(CONFIG.get('vision_gpu_enabled', False)) and detect_gpu()

    # NOTE: Ollama API currently controls model placement; we just call ask_vision.
    try:
        return ask_vision(prompt, image_path, model=model)
    except Exception as e:
        return f"Vision model error: {e}"
