"""
vision.py — VisionEngine: OCR + LLaVA screen describe + webcam
"""

import logging
import os
import subprocess
import tempfile

logger = logging.getLogger(__name__)


def _ollama_unload(model: str = "llava:7b") -> None:
    """Uvolní model z VRAM po dokončení inference (ollama unload)."""
    try:
        import requests as _req
        # Ollama API: POST /api/generate s keep_alive=0 uvolní model
        _req.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "keep_alive": 0},
            timeout=5,
        )
        logger.debug(f"Uvolněn model z VRAM: {model}")
    except Exception:
        pass  # Unload je best-effort, nesmí selhat


def _ask_vision(image_path: str, prompt: str) -> str:
    try:
        # Use vision_pipeline wrapper (GPU selection, fallback)
        from vision_pipeline import describe_with_llava
        result = describe_with_llava(image_path, prompt, model="llava:7b")
        # Po dokončení inference uvolni LLaVA z VRAM
        _ollama_unload("llava:7b")
        return result
    except Exception as e:
        return f"Vision model nedostupný: {e}"


def _take_screenshot() -> str:
    """Pořídí screenshot a vrátí cestu k dočasnému souboru PNG."""
    tmp = tempfile.mktemp(suffix=".png")

    # Zkus scrot
    try:
        result = subprocess.run(["scrot", tmp], capture_output=True, timeout=5)
        if result.returncode == 0 and os.path.exists(tmp):
            return tmp
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: PIL/ImageGrab (Xlib)
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        img.save(tmp, "PNG")
        return tmp
    except Exception:
        pass

    # Fallback: mss
    try:
        import mss
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            from mss.tools import to_png
            to_png(sct_img.rgb, sct_img.size, output=tmp)
            return tmp
    except Exception:
        pass

    raise RuntimeError("Nelze pořídit screenshot — žádný dostupný nástroj")


class VisionEngine:
    """Multimodální vizuální schopnosti: OCR, popis obrazovky, kamera."""

    def screen_ocr(self) -> str:
        """Screenshot + pytesseract OCR → text na obrazovce. Uses cache for performance."""
        try:
            from vision_pipeline import ocr_with_cache
        except Exception:
            return "OCR helper není dostupný"

        try:
            tmp = _take_screenshot()
            try:
                text = ocr_with_cache(tmp)
                return text.strip() or "Na obrazovce nebyl rozpoznán žádný text."
            finally:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
        except Exception as e:
            logger.warning(f"screen_ocr chyba: {e}")
            return f"Chyba OCR: {e}"

    def screen_describe(self) -> str:
        """Screenshot → LLaVA popis obrazovky. Chooses GPU/CPU based on config and hardware."""
        try:
            tmp = _take_screenshot()
            try:
                result = _ask_vision(tmp, "Co vidíš na obrazovce? Popiš obsah stručně česky.")
                return result
            finally:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
        except Exception as e:
            logger.warning(f"screen_describe chyba: {e}")
            return f"LLaVA model není dostupný: {e}"

    def webcam_describe(self) -> str:
        """Snímek z webkamery → LLaVA popis."""
        try:
            import cv2
        except ImportError:
            return "Kamera není dostupná (opencv-python není nainstalován)"

        cap = None
        tmp = None
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return "Kamera není dostupná"

            ret, frame = cap.read()
            if not ret:
                return "Nepodařilo se zachytit snímek z kamery"

            tmp = tempfile.mktemp(suffix=".png")
            cv2.imwrite(tmp, frame)

            result = _ask_vision(tmp, "Co vidíš na tomto snímku z kamery? Popiš obsah stručně česky.")
            return result
        except Exception as e:
            logger.warning(f"webcam_describe chyba: {e}")
            return f"Kamera není dostupná: {e}"
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
            if tmp is not None:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
