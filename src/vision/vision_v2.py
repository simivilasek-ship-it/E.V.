"""
vision_v2.py — JARVIS Vision v2

Layers:
  1. RealTimeScreenMonitor  — kontinuální zachytávání obrazovky, detekce změn
  2. VisionOCRPipeline      — OCR + detekce UI elementů pomocí OpenCV
  3. VisualActionPlanner    — fuzzy match OCR → souřadnice pro kliknutí
"""
from __future__ import annotations

import logging
import os
import tempfile
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Optional dependency flags ─────────────────────────────────────────────────

try:
    import numpy as _np
    HAS_NUMPY = True
except ImportError:
    _np = None  # type: ignore
    HAS_NUMPY = False

try:
    from PIL import Image as _PILImage, ImageChops as _ImageChops
    HAS_PIL = True
except ImportError:
    _PILImage = None  # type: ignore
    _ImageChops = None  # type: ignore
    HAS_PIL = False

try:
    import pytesseract as _tesseract
    HAS_TESSERACT = True
except ImportError:
    _tesseract = None  # type: ignore
    HAS_TESSERACT = False

try:
    import cv2 as _cv2
    HAS_CV2 = True
except ImportError:
    _cv2 = None  # type: ignore
    HAS_CV2 = False

try:
    import pyautogui as _pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    _pyautogui = None  # type: ignore
    HAS_PYAUTOGUI = False


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class BoundingBox:
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass
class ChangeEvent:
    timestamp: float
    region: Optional[BoundingBox]
    diff_score: float  # 0.0-1.0


@dataclass
class UIElement:
    element_type: str       # button | input | label
    text: str
    bbox: BoundingBox
    confidence: float = 1.0


@dataclass
class ScreenAnalysis:
    ocr_text: str
    ui_elements: List[UIElement]
    active_app: str
    clickable_regions: List[BoundingBox]


@dataclass
class ClickAction:
    found: bool
    x: int = 0
    y: int = 0
    matched_text: str = ""
    method: str = "none"     # ocr | vision | none
    error: str = ""


# ── 1. RealTimeScreenMonitor ──────────────────────────────────────────────────

class RealTimeScreenMonitor:
    """
    Kontinualne zachycuje obrazovku (1 FPS) a detekuje zmeny.
    Vola on_change callback s ChangeEvent popisujicim region zmeny.
    """

    DIFF_THRESHOLD = 0.02  # 2 % pixelu se musi zmenit

    def __init__(self, fps: float = 1.0, threshold: float = DIFF_THRESHOLD):
        self.fps = fps
        self.threshold = threshold
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._prev_image: Optional[object] = None  # PIL Image

    @property
    def available(self) -> bool:
        return HAS_PIL and HAS_PYAUTOGUI

    def start(self, on_change: Callable[[ChangeEvent], None]) -> bool:
        """Spusti monitoring na pozadi. Vrati False pokud zavislosti chybi."""
        if not self.available:
            logger.warning("RealTimeScreenMonitor: chybi PIL nebo pyautogui")
            return False
        if self._thread and self._thread.is_alive():
            return True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, args=(on_change,), daemon=True, name="ScreenMonitor"
        )
        self._thread.start()
        logger.info("RealTimeScreenMonitor spusten")
        return True

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)
        self._prev_image = None
        logger.info("RealTimeScreenMonitor zastavem")

    def _capture(self) -> Optional[object]:
        try:
            img = _pyautogui.screenshot()
            return img
        except Exception as e:
            logger.debug("Screenshot selhal: %s", e)
            return None

    def _diff(self, img_a: object, img_b: object) -> Tuple[float, Optional[BoundingBox]]:
        """Vrati (diff_score, bbox) regionu zmeny."""
        try:
            diff = _ImageChops.difference(img_a, img_b)  # type: ignore[arg-type]
            if HAS_NUMPY:
                arr = _np.array(diff)  # type: ignore[arg-type]
                changed = (arr > 10).any(axis=2)
                score = float(changed.mean())
                if score == 0:
                    return 0.0, None
                rows = _np.any(changed, axis=1)
                cols = _np.any(changed, axis=0)
                r_min = int(_np.argmax(rows))
                r_max = int(len(rows) - 1 - _np.argmax(rows[::-1]))
                c_min = int(_np.argmax(cols))
                c_max = int(len(cols) - 1 - _np.argmax(cols[::-1]))
                bbox = BoundingBox(
                    x=c_min, y=r_min,
                    width=max(1, c_max - c_min),
                    height=max(1, r_max - r_min),
                )
                return score, bbox
            else:
                bbox_raw = diff.getbbox()  # type: ignore[attr-defined]
                w, h = img_a.size  # type: ignore[attr-defined]
                total_pixels = w * h
                if bbox_raw:
                    region_pixels = (bbox_raw[2] - bbox_raw[0]) * (bbox_raw[3] - bbox_raw[1])
                    score = region_pixels / total_pixels if total_pixels > 0 else 0.0
                    bbox = BoundingBox(
                        x=bbox_raw[0], y=bbox_raw[1],
                        width=bbox_raw[2] - bbox_raw[0],
                        height=bbox_raw[3] - bbox_raw[1],
                    )
                    return score, bbox
                return 0.0, None
        except Exception as e:
            logger.debug("Diff selhal: %s", e)
            return 0.0, None

    def _loop(self, on_change: Callable[[ChangeEvent], None]) -> None:
        interval = 1.0 / max(self.fps, 0.1)
        while not self._stop_event.is_set():
            try:
                img = self._capture()
                if img is not None and self._prev_image is not None:
                    score, bbox = self._diff(self._prev_image, img)
                    if score > self.threshold:
                        event = ChangeEvent(
                            timestamp=time.time(),
                            region=bbox,
                            diff_score=score,
                        )
                        try:
                            on_change(event)
                        except Exception as cb_err:
                            logger.warning("on_change callback chyba: %s", cb_err)
                if img is not None:
                    self._prev_image = img
            except Exception as e:
                logger.debug("Monitor loop chyba: %s", e)
            self._stop_event.wait(interval)


# ── 2. VisionOCRPipeline ──────────────────────────────────────────────────────

class VisionOCRPipeline:
    """
    Screenshot -> text + UI struktura (OCR + OpenCV detekce regionu).
    """

    def __init__(self, langs: str = "ces+eng"):
        self.langs = langs

    @property
    def available(self) -> bool:
        return HAS_PIL

    def _take_screenshot_to_file(self) -> Optional[str]:
        tmp = tempfile.mktemp(suffix=".png")
        if HAS_PYAUTOGUI:
            try:
                img = _pyautogui.screenshot()
                img.save(tmp, "PNG")
                return tmp
            except Exception as e:
                logger.debug("pyautogui screenshot selhal: %s", e)
        if HAS_PIL:
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab()
                img.save(tmp, "PNG")
                return tmp
            except Exception as e:
                logger.debug("PIL ImageGrab selhal: %s", e)
        try:
            import subprocess
            r = subprocess.run(["scrot", tmp], capture_output=True, timeout=5)
            if r.returncode == 0 and os.path.exists(tmp):
                return tmp
        except Exception:
            pass
        return None

    def _ocr(self, image_path: str) -> Tuple[str, List[dict]]:
        """
        Vrati (plain_text, list of word dicts with bbox).
        word dict: {text, x, y, w, h, conf}
        """
        if not HAS_TESSERACT or not HAS_PIL:
            return "", []
        try:
            img = _PILImage.open(image_path)  # type: ignore[arg-type]
            try:
                data = _tesseract.image_to_data(  # type: ignore[union-attr]
                    img, lang=self.langs, output_type=_tesseract.Output.DICT  # type: ignore[union-attr]
                )
                words: List[dict] = []
                for i in range(len(data["text"])):
                    txt = data["text"][i].strip()
                    raw_conf = data["conf"][i]
                    conf = int(raw_conf) if str(raw_conf).lstrip("-").isdigit() else -1
                    if txt and conf > 30:
                        words.append({
                            "text": txt,
                            "x": data["left"][i],
                            "y": data["top"][i],
                            "w": data["width"][i],
                            "h": data["height"][i],
                            "conf": conf,
                        })
                plain = " ".join(w["text"] for w in words)
                return plain, words
            except Exception:
                plain = _tesseract.image_to_string(img, lang=self.langs)  # type: ignore[union-attr]
                return plain.strip(), []
        except Exception as e:
            logger.warning("OCR selhal: %s", e)
            return "", []

    def _detect_ui_regions(self, image_path: str) -> List[BoundingBox]:
        """Detekce obdelnikovych regionu pomoci OpenCV (potencialni tlacitka/pole)."""
        if not HAS_CV2:
            return []
        try:
            img = _cv2.imread(image_path)  # type: ignore[union-attr]
            if img is None:
                return []
            gray = _cv2.cvtColor(img, _cv2.COLOR_BGR2GRAY)  # type: ignore[union-attr]
            blurred = _cv2.GaussianBlur(gray, (3, 3), 0)  # type: ignore[union-attr]
            edges = _cv2.Canny(blurred, 50, 150)  # type: ignore[union-attr]
            contours, _ = _cv2.findContours(  # type: ignore[union-attr]
                edges, _cv2.RETR_EXTERNAL, _cv2.CHAIN_APPROX_SIMPLE  # type: ignore[union-attr]
            )
            boxes: List[BoundingBox] = []
            for cnt in contours:
                x, y, w, h = _cv2.boundingRect(cnt)  # type: ignore[union-attr]
                if w < 20 or h < 10:
                    continue
                if w > img.shape[1] * 0.9 or h > img.shape[0] * 0.9:
                    continue
                peri = _cv2.arcLength(cnt, True)  # type: ignore[union-attr]
                approx = _cv2.approxPolyDP(cnt, 0.04 * peri, True)  # type: ignore[union-attr]
                if len(approx) == 4:
                    boxes.append(BoundingBox(x=x, y=y, width=w, height=h))
            return boxes
        except Exception as e:
            logger.warning("OpenCV detekce selhal: %s", e)
            return []

    def _classify_element(self, bbox: BoundingBox, words: List[dict]) -> Optional[UIElement]:
        """Klasifikuj region jako button/input/label podle velikosti a textu."""
        region_texts: List[str] = []
        for w in words:
            wx = w["x"] + w["w"] // 2
            wy = w["y"] + w["h"] // 2
            if (bbox.x <= wx <= bbox.x + bbox.width and
                    bbox.y <= wy <= bbox.y + bbox.height):
                region_texts.append(w["text"])
        text = " ".join(region_texts)

        area = bbox.width * bbox.height
        aspect = bbox.width / max(bbox.height, 1)

        if area < 5000 and text:
            el_type = "button"
        elif aspect > 4 and bbox.height < 50:
            el_type = "input"
        elif text:
            el_type = "button" if area < 10000 else "input"
        else:
            return None

        return UIElement(element_type=el_type, text=text, bbox=bbox)

    def _get_active_app(self) -> str:
        try:
            import subprocess
            r = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=2
            )
            if r.returncode == 0:
                return r.stdout.strip()
        except Exception:
            pass
        return "unknown"

    def analyze(self, screenshot_path: Optional[str] = None) -> ScreenAnalysis:
        """
        Poridi screenshot (nebo pouzije predany) a vrati ScreenAnalysis.
        """
        path = screenshot_path
        own_file = False
        if path is None:
            path = self._take_screenshot_to_file()
            own_file = True

        if path is None or not os.path.exists(path):
            return ScreenAnalysis(ocr_text="", ui_elements=[], active_app="", clickable_regions=[])

        try:
            ocr_text, words = self._ocr(path)
            cv_boxes = self._detect_ui_regions(path)

            ui_elements: List[UIElement] = []
            for bbox in cv_boxes:
                el = self._classify_element(bbox, words)
                if el is not None:
                    ui_elements.append(el)

            clickable = [el.bbox for el in ui_elements if el.element_type in ("button", "input")]
            active_app = self._get_active_app()

            return ScreenAnalysis(
                ocr_text=ocr_text,
                ui_elements=ui_elements,
                active_app=active_app,
                clickable_regions=clickable,
            )
        finally:
            if own_file and path and os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception:
                    pass


# ── 3. VisualActionPlanner ────────────────────────────────────────────────────

class VisualActionPlanner:
    """
    Vezme instrukci (textovy popis) a vrati koordinaty pro kliknuti.
    Postup: OCR match -> fuzzy match -> fallback LLaVA/Groq vision.
    """

    def __init__(self) -> None:
        self._pipeline = VisionOCRPipeline()

    @property
    def available(self) -> bool:
        return True  # Vzdy dostupny (ma fallbacky)

    def _fuzzy_score(self, query: str, candidate: str) -> float:
        """Jednoduchy fuzzy match: pocet spolecnych slov / max delka."""
        q_words = set(query.lower().split())
        c_words = set(candidate.lower().split())
        if not q_words or not c_words:
            return 0.0
        common = q_words & c_words
        return len(common) / max(len(q_words), len(c_words))

    def _ocr_find(self, instruction: str, path: str) -> Optional[Tuple[int, int, str]]:
        """OCR-based find. Vrati (x, y, matched_text) nebo None."""
        if not HAS_TESSERACT or not HAS_PIL:
            return None
        try:
            img = _PILImage.open(path)  # type: ignore[arg-type]
            data = _tesseract.image_to_data(  # type: ignore[union-attr]
                img, output_type=_tesseract.Output.DICT  # type: ignore[union-attr]
            )
            best_score = 0.0
            best_pos: Optional[Tuple[int, int, str]] = None
            for i in range(len(data["text"])):
                txt = data["text"][i].strip()
                if not txt:
                    continue
                score = self._fuzzy_score(instruction, txt)
                if score > best_score:
                    best_score = score
                    cx = data["left"][i] + data["width"][i] // 2
                    cy = data["top"][i] + data["height"][i] // 2
                    best_pos = (cx, cy, txt)
            if best_score >= 0.4 and best_pos is not None:
                return best_pos
        except Exception as e:
            logger.debug("OCR find selhal: %s", e)
        return None

    def _vision_find(self, instruction: str, path: str) -> Optional[Tuple[int, int, str]]:
        """Fallback: LLaVA/Groq vision pro lokalizaci elementu."""
        try:
            import re
            from vision_pipeline import describe_with_llava
            prompt = (
                "Na obrazku najdi element: '" + instruction + "'. "
                "Odpovez POUZE souradnicemi ve formatu X:cislo Y:cislo (stred elementu). "
                "Priklad: X:320 Y:240"
            )
            response = describe_with_llava(path, prompt, model="llava:7b")
            m = re.search(r"X[:\s]+(\d+)[,\s]+Y[:\s]+(\d+)", response, re.IGNORECASE)
            if m:
                return (int(m.group(1)), int(m.group(2)), instruction)
        except Exception as e:
            logger.debug("Vision fallback selhal: %s", e)
        return None

    def find_and_click(self, instruction: str) -> ClickAction:
        """
        1. Poridi screenshot
        2. Spusti OCR -> fuzzy match (~50ms)
        3. Fallback: LLaVA vision (~2s)
        Vrati ClickAction s koordinaty.
        """
        tmp = self._pipeline._take_screenshot_to_file()
        if tmp is None:
            return ClickAction(found=False, error="Nelze poridit screenshot")

        try:
            result = self._ocr_find(instruction, tmp)
            if result:
                x, y, text = result
                return ClickAction(found=True, x=x, y=y, matched_text=text, method="ocr")

            result = self._vision_find(instruction, tmp)
            if result:
                x, y, text = result
                return ClickAction(found=True, x=x, y=y, matched_text=text, method="vision")

            return ClickAction(found=False, error="Element nenalezen: '" + instruction + "'")
        except Exception as e:
            return ClickAction(found=False, error=str(e))
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except Exception:
                    pass


# ── Singleton helpers ─────────────────────────────────────────────────────────

_monitor: Optional[RealTimeScreenMonitor] = None
_pipeline: Optional[VisionOCRPipeline] = None
_planner: Optional[VisualActionPlanner] = None


def get_monitor() -> RealTimeScreenMonitor:
    global _monitor
    if _monitor is None:
        _monitor = RealTimeScreenMonitor()
    return _monitor


def get_pipeline() -> VisionOCRPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = VisionOCRPipeline()
    return _pipeline


def get_planner() -> VisualActionPlanner:
    global _planner
    if _planner is None:
        _planner = VisualActionPlanner()
    return _planner
