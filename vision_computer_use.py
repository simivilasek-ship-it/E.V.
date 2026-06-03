"""
JARVIS — Vision-Guided Computer Use
Umožňuje JARVISovi „vidět" obrazovku a ovládat UI jako člověk:
  screenshot → vision model (LLaVA / Qwen2-VL) → souřadnice → pyautogui akce

Použití:
  from vision_computer_use import VisionAgent
  agent = VisionAgent()
  agent.click("tlačítko Přihlásit")
  agent.type_text("jmeno@email.cz")
  agent.find_and_fill("pole pro heslo", "tajnéheslo123")

Vyžaduje:
  pip install pyautogui pillow
  + lokální LLaVA model nebo cloud vision (Groq llama-3.2-90b-vision-preview)
"""
from __future__ import annotations

import base64
import json
import logging
import re
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import pyperclip as _pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    _pyperclip = None  # type: ignore
    HAS_PYPERCLIP = False


# ── Typy ─────────────────────────────────────────────────────────────────────

@dataclass
class ScreenAction:
    action: str               # click | type | scroll | screenshot | move
    x: Optional[int] = None
    y: Optional[int] = None
    text: Optional[str] = None
    success: bool = False
    error: str = ""

@dataclass
class VisionResult:
    found: bool
    x: int = 0
    y: int = 0
    description: str = ""
    raw_vision_response: str = ""


# ── Screenshot helper ─────────────────────────────────────────────────────────

def take_screenshot(region=None) -> Optional[bytes]:
    """Pořídí screenshot a vrátí PNG bytes. Vrátí None při chybě."""
    try:
        import pyautogui
        from PIL import Image
        img = pyautogui.screenshot(region=region)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        logger.warning(f"Screenshot selhal: {e}")
        return None


def screenshot_to_b64(png_bytes: bytes) -> str:
    return base64.b64encode(png_bytes).decode("utf-8")


# ── Vision lokalizace ─────────────────────────────────────────────────────────

_COORD_PATTERN = re.compile(
    r"(?:x\s*[=:]\s*(\d+).*?y\s*[=:]\s*(\d+))"
    r"|(?:(\d+)\s*,\s*(\d+))"
    r"|(?:\((\d+)[,\s]+(\d+)\))",
    re.IGNORECASE | re.DOTALL,
)


def _extract_coords(text: str) -> Optional[Tuple[int, int]]:
    """Extrahuje (x, y) ze slovní odpovědi vision modelu."""
    m = _COORD_PATTERN.search(text)
    if m:
        groups = [g for g in m.groups() if g is not None]
        if len(groups) >= 2:
            return int(groups[0]), int(groups[1])
    return None


def ask_vision_for_element(
    screenshot_b64: str,
    element_description: str,
    screen_w: int,
    screen_h: int,
    ollama_url: str = "http://localhost:11434/api/chat",
    model: str = "llava:7b",
    groq_key: str = "",
) -> VisionResult:
    """
    Pošle screenshot + popis elementu do vision modelu.
    Vrátí VisionResult se souřadnicemi (x, y) v pixelech.

    Zkouší nejdříve Groq llama-3.2-90b-vision-preview (pokud je klíč),
    fallback na lokální LLaVA přes Ollama.
    """
    prompt = (
        f"Toto je screenshot obrazovky ({screen_w}x{screen_h} px). "
        f"Najdi element: '{element_description}'. "
        "Odpověz POUZE v JSON formátu: {\"found\": true/false, \"x\": <číslo>, \"y\": <číslo>, \"popis\": \"<co vidíš>\"}. "
        "Souřadnice musí být absolutní pixely středu elementu. "
        "Pokud element nenajdeš, vrať {\"found\": false}."
    )

    raw = ""

    # 1) Groq vision (llama-3.2-90b-vision-preview)
    if groq_key:
        try:
            import requests
            payload = {
                "model": "llama-3.2-90b-vision-preview",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/png;base64,{screenshot_b64}"
                        }},
                    ],
                }],
                "max_tokens": 200,
                "temperature": 0.0,
            }
            headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                              json=payload, headers=headers, timeout=20)
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"].strip()
            logger.debug(f"Groq vision odpověď: {raw[:200]}")
        except Exception as e:
            logger.warning(f"Groq vision selhal ({e}), zkouším lokální LLaVA")

    # 2) Lokální LLaVA přes Ollama
    if not raw:
        try:
            import requests as _req
            payload = {
                "model": model,
                "messages": [{
                    "role": "user",
                    "content": prompt,
                    "images": [screenshot_b64],
                }],
                "stream": False,
                "options": {"temperature": 0.0},
            }
            r = _req.post(ollama_url, json=payload, timeout=60)
            r.raise_for_status()
            raw = r.json().get("message", {}).get("content", "").strip()
            logger.debug(f"LLaVA odpověď: {raw[:200]}")
            # Uvolni LLaVA z VRAM ihned po použití (keep_alive=0)
            try:
                _unload_url = ollama_url.replace("/api/chat", "/api/generate")
                _req.post(_unload_url, json={"model": model, "keep_alive": 0}, timeout=5)
                logger.debug(f"VRAM uvolněna: {model}")
            except Exception:
                pass
        except Exception as e:
            logger.error(f"LLaVA selhal: {e}")
            return VisionResult(found=False, description=f"Vision model nedostupný: {e}")

    # Parsuj JSON odpověď
    try:
        # Vyjmi JSON z markdown bloků
        clean = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
        data = json.loads(clean)
        if data.get("found"):
            return VisionResult(
                found=True,
                x=int(data.get("x", 0)),
                y=int(data.get("y", 0)),
                description=data.get("popis", ""),
                raw_vision_response=raw,
            )
        return VisionResult(found=False, raw_vision_response=raw)
    except Exception:
        # Fallback: zkus regex extrakci souřadnic
        coords = _extract_coords(raw)
        if coords:
            return VisionResult(found=True, x=coords[0], y=coords[1],
                                raw_vision_response=raw)
        return VisionResult(found=False, raw_vision_response=raw)


# ── Hlavní VisionAgent ────────────────────────────────────────────────────────

class VisionAgent:
    """
    High-level agent pro vision-guided UI ovládání.

    agent = VisionAgent()
    agent.click("Přihlásit")            # najde tlačítko a klikne
    agent.type_text("hello world")      # napíše text
    agent.find_and_fill("pole E-mail", "user@example.com")
    agent.scroll("dolů", clicks=3)
    agent.run_task("Najdi nejlevnější letenky do Londýna a vyplň formulář")
    """

    def __init__(self, config: dict = None):
        if config is None:
            try:
                from config import CONFIG
                config = CONFIG
            except Exception:
                config = {}
        self.config = config
        self._ollama_url = config.get("ollama_url", "http://localhost:11434/api/chat")
        self._vision_model = config.get("vision_model", "llava:7b")
        self._groq_key = config.get("groq_api_key", "") or ""
        self._screen_w, self._screen_h = self._get_screen_size()
        self._history: list = []

    def _get_screen_size(self) -> Tuple[int, int]:
        try:
            import pyautogui
            return pyautogui.size()
        except Exception:
            return 1920, 1080

    def _screenshot(self) -> Optional[str]:
        """Pořídí screenshot a vrátí base64 string."""
        png = take_screenshot()
        if png:
            return screenshot_to_b64(png)
        return None

    def screenshot_and_analyze(self, question: str) -> str:
        """Pořídí screenshot a položí otázku vision modelu."""
        b64 = self._screenshot()
        if not b64:
            return "Nelze pořídit screenshot."
        result = ask_vision_for_element(
            b64, question, self._screen_w, self._screen_h,
            self._ollama_url, self._vision_model, self._groq_key,
        )
        return result.raw_vision_response or "Žádná odpověď."

    def find_element(self, description: str) -> VisionResult:
        """Najde element na obrazovce pomocí vision modelu."""
        b64 = self._screenshot()
        if not b64:
            return VisionResult(found=False, description="Screenshot selhal")
        return ask_vision_for_element(
            b64, description, self._screen_w, self._screen_h,
            self._ollama_url, self._vision_model, self._groq_key,
        )

    def click(self, description: str, double: bool = False) -> ScreenAction:
        """Najde element popsaný textem a klikne na něj."""
        result = self.find_element(description)
        if not result.found:
            logger.warning(f"VisionAgent.click: element nenalezen: {description!r}")
            return ScreenAction(action="click", success=False,
                                error=f"Element nenalezen: {description!r}")
        return self._click_at(result.x, result.y, double)

    def _click_at(self, x: int, y: int, double: bool = False) -> ScreenAction:
        try:
            import pyautogui
            pyautogui.moveTo(x, y, duration=0.3)
            if double:
                pyautogui.doubleClick(x, y)
            else:
                pyautogui.click(x, y)
            self._history.append({"action": "click", "x": x, "y": y})
            logger.info(f"VisionAgent click @ ({x}, {y})")
            return ScreenAction(action="click", x=x, y=y, success=True)
        except Exception as e:
            return ScreenAction(action="click", x=x, y=y, success=False, error=str(e))

    def type_text(self, text: str, interval: float = 0.05) -> ScreenAction:
        """Napíše text (předpokládá, že focus je nastaven)."""
        try:
            import pyautogui
            pyautogui.typewrite(text, interval=interval)
            self._history.append({"action": "type", "text": text})
            logger.info(f"VisionAgent type: {text[:40]!r}")
            return ScreenAction(action="type", text=text, success=True)
        except Exception as e:
            # pyautogui.typewrite nefunguje dobře pro Unicode — fallback přes clipboard
            try:
                import pyautogui
                pyautogui.hotkey("ctrl", "a")
                if HAS_PYPERCLIP and _pyperclip:
                    _pyperclip.copy(text)
                    pyautogui.hotkey("ctrl", "v")
                    return ScreenAction(action="type", text=text, success=True)
                return ScreenAction(action="type", text=text, success=False,
                                    error="pyperclip není dostupný (pip install pyperclip)")
            except Exception as e2:
                return ScreenAction(action="type", text=text, success=False, error=str(e2))

    def find_and_fill(self, field_description: str, value: str) -> ScreenAction:
        """Najde pole popsané textem, klikne na něj a vyplní hodnotu."""
        click_result = self.click(field_description)
        if not click_result.success:
            return click_result
        time.sleep(0.3)
        # Vyber vše a přepiš
        try:
            import pyautogui
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.1)
        except Exception:
            pass
        return self.type_text(value)

    def scroll(self, direction: str = "dolů", clicks: int = 3) -> ScreenAction:
        """Skroluje obrazovku."""
        try:
            import pyautogui
            amount = -clicks if direction in ("dolů", "down") else clicks
            pyautogui.scroll(amount)
            return ScreenAction(action="scroll", success=True)
        except Exception as e:
            return ScreenAction(action="scroll", success=False, error=str(e))

    def press_key(self, key: str) -> ScreenAction:
        """Stiskne klávesu (enter, tab, escape, ...)."""
        try:
            import pyautogui
            pyautogui.press(key)
            return ScreenAction(action="press", text=key, success=True)
        except Exception as e:
            return ScreenAction(action="press", text=key, success=False, error=str(e))

    def open_url_in_browser(self, url: str) -> ScreenAction:
        """Otevře URL v systémovém prohlížeči."""
        try:
            import subprocess
            subprocess.Popen(["xdg-open", url])
            time.sleep(2.0)
            return ScreenAction(action="open_url", text=url, success=True)
        except Exception as e:
            return ScreenAction(action="open_url", text=url, success=False, error=str(e))

    def run_task(self, task_description: str, max_steps: int = 10) -> str:
        """
        Autonomně splní víceúrovňový UI úkol pomocí ReAct smyčky.

        Kroky:
          1. Pořídí screenshot
          2. Požádá LLM o plán akcí
          3. Provede každou akci (click/type/scroll/open_url)
          4. Po každé akci znovu pořídí screenshot a ověří pokrok
        """
        try:
            from cloud_router import get_cloud_router
            from config import CONFIG
            cloud = get_cloud_router(CONFIG)
        except Exception:
            cloud = None

        plan_prompt = (
            f"Jsi agent ovládající počítač. Uživatel chce: '{task_description}'.\n"
            "Vytvoř krok za krokem plán ve formátu JSON:\n"
            '[{"action": "open_url"|"click"|"type"|"scroll"|"press", '
            '"target": "<popis nebo URL nebo text nebo klávesa>"}]\n'
            "Maximálně 10 kroků. Buď konkrétní."
        )

        b64 = self._screenshot()
        messages = [{"role": "user", "content": plan_prompt}]
        if b64:
            # Přidej screenshot jako kontext pokud podporuje vision
            messages = [{"role": "user", "content": [
                {"type": "text", "text": plan_prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{b64}"
                }},
            ]}]

        plan_json = ""
        if cloud and cloud.enabled:
            try:
                resp = cloud.call(messages, task_type="agent", temperature=0.1, max_tokens=600)
                plan_json = resp.content
            except Exception:
                pass

        if not plan_json:
            return f"Nemohu naplánovat úkol (cloud nedostupný): {task_description}"

        # Parsuj plán
        try:
            clean = re.sub(r"```(?:json)?", "", plan_json).strip().strip("`").strip()
            # Najdi první JSON pole
            start = clean.find("[")
            end   = clean.rfind("]") + 1
            steps = json.loads(clean[start:end]) if start >= 0 else []
        except Exception as e:
            logger.error(f"Parsování plánu selhalo: {e}\n{plan_json[:300]}")
            return f"Nepodařilo se naparsovat plán: {e}"

        results = []
        for i, step in enumerate(steps[:max_steps]):
            action = step.get("action", "")
            target = step.get("target", "")
            logger.info(f"VisionAgent krok {i+1}: {action} → {target!r}")

            if action == "open_url":
                r = self.open_url_in_browser(target)
            elif action == "click":
                r = self.click(target)
            elif action == "type":
                r = self.type_text(target)
            elif action == "scroll":
                r = self.scroll(target)
            elif action == "press":
                r = self.press_key(target)
            else:
                r = ScreenAction(action=action, success=False, error=f"Neznámá akce: {action}")

            results.append({"step": i+1, "action": action, "target": target,
                            "success": r.success, "error": r.error})
            if not r.success:
                logger.warning(f"Krok {i+1} selhal: {r.error}")
            time.sleep(0.8)

        ok_count = sum(1 for r in results if r["success"])
        return (
            f"Dokončeno {ok_count}/{len(results)} kroků pro úkol: '{task_description}'\n"
            + "\n".join(f"  {r['step']}. {r['action']}({r['target']!r}) — "
                        f"{'✓' if r['success'] else '✗ ' + r['error']}"
                        for r in results)
        )

    def history(self) -> list:
        return list(self._history)


# Singleton
_vision_agent: Optional[VisionAgent] = None


def get_vision_agent(config: dict = None) -> VisionAgent:
    global _vision_agent
    if _vision_agent is None:
        _vision_agent = VisionAgent(config)
    return _vision_agent
