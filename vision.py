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


def _identify_app_from_title(title: str) -> str:
    """Odvodí aplikaci z titulku okna — bez halucinací."""
    t = title.lower()
    if "cursor" in t:
        return "Cursor"
    if "firefox" in t:
        return "Firefox"
    if "google chrome" in t or " chromium" in t:
        return "Chrome"
    if "jarvis" in t:
        return "E.V."
    if "visual studio code" in t or t.endswith(" - code"):
        return "VS Code"
    if "zed " in t or t.startswith("zed"):
        return "Zed"
    if "jetbrains" in t or "intellij" in t or "pycharm" in t:
        return "JetBrains IDE"
    if "terminal" in t or "konsole" in t or "alacritty" in t or "kitty" in t:
        return "Terminál"
    return ""


def _collect_desktop_context() -> dict:
    """Spolehlivý kontext z OS — aktivní okno + seznam oken."""
    try:
        from config import CONFIG
        from context_orchestrator import get_context_orchestrator

        orch = get_context_orchestrator(CONFIG)
        return {
            "active": orch._get_active_window(),
            "windows": orch._get_open_windows(),
        }
    except Exception as e:
        logger.debug(f"desktop context selhal: {e}")
        return {"active": "", "windows": []}


def _ocr_snippet(image_path: str, limit: int = 600) -> str:
    try:
        from vision_pipeline import ocr_with_cache
        text = (ocr_with_cache(image_path) or "").strip()
        if not text or text.startswith("OCR chyba"):
            return ""
        # Odstraň opakující se krátké řádky (šum z UI)
        lines: list[str] = []
        seen: set[str] = set()
        for line in text.splitlines():
            line = line.strip()
            if len(line) < 3 or line.lower() in seen:
                continue
            seen.add(line.lower())
            lines.append(line)
        snippet = "\n".join(lines)
        return snippet[:limit] + ("…" if len(snippet) > limit else "")
    except Exception:
        return ""


def _format_factual_screen_report(ctx: dict, ocr: str = "", question: str = "") -> str:
    """Popis obrazovky jen z ověřitelných dat — bez vymýšlení."""
    active = (ctx.get("active") or "").strip()
    windows = [w for w in (ctx.get("windows") or []) if w and w != active]

    parts: list[str] = []

    if active:
        app = _identify_app_from_title(active)
        if app:
            parts.append(f"V popředí máš {app} — „{active}“.")
        else:
            parts.append(f"V popředí je okno „{active}“.")
    else:
        parts.append("Aktivní okno se nepodařilo zjistit.")

    if windows:
        shown = windows[:6]
        labels = []
        for w in shown:
            app = _identify_app_from_title(w)
            labels.append(f"{app} ({w})" if app else w)
        parts.append("Další okna: " + "; ".join(labels) + ".")

    if ocr:
        parts.append(f"Na obrazovce je text: {ocr[:300]}{'…' if len(ocr) > 300 else ''}")

    if not active and not windows and not ocr:
        return (
            "Nepodařilo se zjistit, co máš otevřené. "
            "Pro lepší popis: ollama pull llava:7b"
        )

    return "\n".join(parts)


def _build_grounded_vision_prompt(ctx: dict, ocr: str, question: str) -> str:
    active = ctx.get("active") or "neznámé"
    windows = ", ".join(ctx.get("windows") or []) or "žádná"
    return (
        f"Otázka uživatele: {question or 'Co je na obrazovce?'}\n\n"
        f"OVĚŘENÁ DATA Z OS (musíš je respektovat):\n"
        f"- Aktivní okno: {active}\n"
        f"- Otevřená okna: {windows}\n"
        f"- OCR text: {ocr or '(prázdný)'}\n\n"
        "Pravidla: Odpověz stručně česky. Používej POUZE výše uvedená data a screenshot. "
        "NEVYMÝŠLEJ aplikace ani okna. Pokud titulek obsahuje 'Cursor', neříkej VS Code. "
        "Když si nejsi jistý, napiš že to z obrázku nejde spolehlivě určit."
    )


def _ask_vision(image_path: str, prompt: str) -> str:
    try:
        from vision_pipeline import describe_with_llava
        from config import CONFIG

        model = CONFIG.get("vision_model", "llava:7b")
        result = describe_with_llava(image_path, prompt, model=model)
        _ollama_unload(model)
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

    def screen_describe(self, question: str = "") -> str:
        """Popis obrazovky — primárně z názvů oken (spolehlivé), volitelně LLaVA."""
        ctx = _collect_desktop_context()
        tmp = None
        ocr = ""
        try:
            try:
                tmp = _take_screenshot()
                ocr = _ocr_snippet(tmp)
            except Exception as e:
                logger.debug(f"screenshot/OCR přeskočeno: {e}")

            # Vždy nejdřív faktický report z OS
            factual = _format_factual_screen_report(ctx, ocr, question)

            # Vision model jen jako doplněk, s grounded promptem
            if tmp:
                from llm import _pick_vision_model
                from config import CONFIG

                url = CONFIG.get("ollama_url", "http://localhost:11434/api/chat")
                if _pick_vision_model(CONFIG.get("vision_model", "llava:7b"), url):
                    prompt = _build_grounded_vision_prompt(ctx, ocr, question)
                    vision_extra = _ask_vision(tmp, prompt)
                    if vision_extra and not vision_extra.startswith(("Chyba", "Vision model")):
                        return f"{factual}\n\n**Detail ze screenshotu:**\n{vision_extra}"

            return factual
        except Exception as e:
            logger.warning(f"screen_describe chyba: {e}")
            return _format_factual_screen_report(ctx, ocr, question) or f"Popis obrazovky selhal: {e}"
        finally:
            if tmp:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

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
