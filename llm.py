"""
JARVIS v2.0 — LLM komunikace
"""

import os
import re
import json
import requests
import logging
from typing import Dict, Tuple
from collections import deque

logger = logging.getLogger(__name__)

_HOME = os.path.expanduser("~")
_USER = os.environ.get("USER", os.path.basename(_HOME))

SYSTEM_PROMPT = f"""Jsi JARVIS, osobní hlasový asistent běžící lokálně na počítači uživatele.
Systém: uživatel={_USER}, domov={_HOME}, OS=Linux
Cesty vždy začínají {_HOME}/ — nikdy /home/user/

Tvým úkolem je rozumět tomu, co uživatel chce, a podle toho buď:
1) provést systémový příkaz
2) nebo odpovědět jako inteligentní AI asistent

---

### 1) KDYŽ UŽIVATEL CHCE PROVÉST PŘÍKAZ
Vrať výstup ve formátu:

COMMAND: <název_příkazu>
ARGS: <argumenty>

Příklady:
- "vypni počítač" → COMMAND: shutdown
- "otevři chrome" → COMMAND: open_app\\nARGS: chrome
- "zvýš jas na 80%" → COMMAND: set_brightness\\nARGS: 80
- "zastav discord" → COMMAND: kill_process\\nARGS: discord
- "počasí Praha" → COMMAND: weather\\nARGS: Praha
- "zahraj Justin Bieber" → COMMAND: youtube_play\\nARGS: Justin Bieber
- "vytvoř složku projekt" → COMMAND: create_folder\\nARGS: {_HOME}/projekt
- "timer 5 minut" → COMMAND: set_timer\\nARGS: 300 Timer
- "hlasitost 60" → COMMAND: volume\\nARGS: 60
- "screenshot" → COMMAND: screenshot

Dostupné příkazy (z commands.py):
open_app, open_url, search_web, write_text, type_key,
volume, set_brightness, media, screenshot, open_file,
clipboard_set, system_info, get_time, get_date,
set_timer, kill_process, write_email,
youtube_play, create_folder, create_file, delete_file,
move_file, find_files, install_app, uninstall_app,
update_system, sleep_pc, shutdown, restart,
vscode_open, vscode_new_file, run_script, weather, answer

---

### 2) KDYŽ UŽIVATEL NECHCE PŘÍKAZ
Odpověz jako plnohodnotný AI asistent — normální textová odpověď bez COMMAND.

---

### 3) ROZHODOVÁNÍ — KLÍČOVÉ PRAVIDLO
Otázky, vysvětlení a konverzace NIKDY nevrací COMMAND. Příklady:
- "umíš jazyk C?" → normální odpověď (NE příkaz)
- "co je Python?" → normální odpověď
- "napiš mi funkci fibonacci" → napiš kód jako odpověď
- "jak funguje rekurze?" → vysvětli
- "co umíš?" → vysvětli schopnosti
- "ahoj" / "jak se máš?" → normální konverzace
Příkazy jsou POUZE akce se systémem: otevřít, zavřít, vypnout, nastavit, najít soubor atd.

---

### 4) STYL
- stručný, jasný, věcný
- v češtině
- neomlouvej se zbytečně"""


# Mapování ARGS → params dict pro každý příkaz
def _parse_args(command: str, args: str) -> dict:
    a = args.strip()
    try:
        if command == "open_app":
            return {"app": a}
        elif command == "open_url":
            return {"url": a if a.startswith("http") else "https://" + a}
        elif command == "search_web":
            return {"query": a}
        elif command == "write_text":
            return {"text": a}
        elif command == "type_key":
            return {"key": a}
        elif command == "kill_process":
            return {"name": a}
        elif command == "set_brightness":
            return {"level": int(re.sub(r"[^\d]", "", a) or "50")}
        elif command == "volume":
            digits = re.sub(r"[^\d]", "", a)
            if digits:
                return {"level": int(digits)}
            return {"action": a}
        elif command == "weather":
            return {"city": a}
        elif command == "youtube_play":
            parts = a.split("|")
            query = parts[0].strip()
            idx   = int(parts[1].strip()) if len(parts) > 1 else 1
            audio = parts[2].strip().lower() == "true" if len(parts) > 2 else False
            return {"query": query, "index": idx, "audio_only": audio}
        elif command in ("create_folder", "create_file", "delete_file",
                         "open_file", "run_script", "vscode_open"):
            return {"path": os.path.expanduser(a)}
        elif command == "find_files":
            parts = a.split(" in ", 1)
            return {"name": parts[0].strip(),
                    "path": os.path.expanduser(parts[1].strip()) if len(parts) > 1 else _HOME}
        elif command == "move_file":
            parts = a.split(" -> ", 1)
            if len(parts) == 2:
                return {"src": os.path.expanduser(parts[0].strip()),
                        "dst": os.path.expanduser(parts[1].strip())}
            return {"src": a, "dst": ""}
        elif command in ("install_app", "uninstall_app"):
            return {"name": a}
        elif command == "set_timer":
            parts = a.split(None, 1)
            seconds = int(parts[0]) if parts[0].isdigit() else 60
            label   = parts[1] if len(parts) > 1 else "Timer"
            return {"seconds": seconds, "label": label}
        elif command == "media":
            return {"action": a}
        elif command in ("shutdown", "restart"):
            digits = re.sub(r"[^\d]", "", a)
            return {"delay": int(digits)} if digits else {}
        elif command == "clipboard_set":
            return {"text": a}
        elif command in ("write_email",):
            parts = a.split("|")
            return {
                "to":      parts[0].strip() if len(parts) > 0 else "",
                "subject": parts[1].strip() if len(parts) > 1 else "",
                "body":    parts[2].strip() if len(parts) > 2 else "",
            }
    except Exception:
        pass
    return {}


class LLMEngine:

    def __init__(self, config: dict):
        self.config = config
        self.url    = config["ollama_url"]
        self.model  = config["ollama_model"]
        self.history: deque = deque(maxlen=config.get("history_size", 20))
        logger.info(f"LLM: {self.model} @ {self.url}")

    def ask(self, user_text: str) -> Tuple[str, Dict]:
        self.history.append({"role": "user", "content": user_text})

        payload = {
            "model":    self.model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                         *list(self.history)],
            "stream":   False,
            "options":  {"temperature": 0.1, "num_predict": 400},
        }

        for attempt in range(2):
            try:
                resp = requests.post(self.url, json=payload, timeout=30)
                resp.raise_for_status()
                raw = resp.json().get("message", {}).get("content", "").strip()
                logger.debug(f"[LLM #{attempt+1}] {raw[:200]}")

                message, action_data = self._parse_response(raw)

                # Retry pokud první pokus nevrátil příkaz ani smysluplnou odpověď
                if attempt == 0 and action_data["action"] == "answer" and not message.strip():
                    continue

                self.history.append({"role": "assistant", "content": raw})
                return message, action_data

            except requests.Timeout:
                self.history.pop() if self.history else None
                return "Ollama nereaguje (timeout).", {"action": "answer", "params": {}}
            except Exception as e:
                self.history.pop() if self.history else None
                return f"Chyba: {e}", {"action": "answer", "params": {}}

        self.history.pop() if self.history else None
        return "Nepodařilo se zpracovat.", {"action": "answer", "params": {}}

    def _parse_response(self, raw: str) -> Tuple[str, Dict]:
        # Najdi COMMAND: a volitelně ARGS:
        cmd_match  = re.search(r"COMMAND:\s*(\w+)", raw)
        args_match = re.search(r"ARGS:\s*(.+?)(?:\n|$)", raw)

        if cmd_match:
            command = cmd_match.group(1).strip()
            args    = args_match.group(1).strip() if args_match else ""

            # Zpráva = text PŘED příkazem (pokud existuje)
            before = raw[:cmd_match.start()].strip()
            message = before if before else self._default_message(command, args)

            params = _parse_args(command, args)
            return message, {"action": command, "params": params}

        # Žádný příkaz → AI odpověď
        return raw, {"action": "answer", "params": {}}

    def _default_message(self, command: str, args: str) -> str:
        msgs = {
            "open_app":      f"Otevírám {args}.",
            "open_url":      f"Otevírám stránku.",
            "search_web":    f"Hledám: {args}.",
            "youtube_play":  f"Přehrávám: {args}.",
            "weather":       f"Zjišťuji počasí v {args}.",
            "shutdown":      "Vypínám počítač.",
            "restart":       "Restartuji počítač.",
            "sleep_pc":      "Uspávám počítač.",
            "screenshot":    "Pořizuji screenshot.",
            "system_info":   "Zjišťuji stav systému.",
            "get_time":      "Zjišťuji čas.",
            "get_date":      "Zjišťuji datum.",
            "set_timer":     f"Nastavuji timer.",
            "create_folder": f"Vytvářím složku.",
            "create_file":   f"Vytvářím soubor.",
            "delete_file":   f"Mažu soubor.",
            "kill_process":  f"Ukončuji {args}.",
            "volume":        f"Nastavuji hlasitost.",
            "set_brightness":f"Nastavuji jas na {args}%.",
            "install_app":   f"Instaluji {args}.",
            "vscode_open":   f"Otevírám ve VSCode.",
        }
        return msgs.get(command, "Provádím akci.")

    def stream_ask(self, user_text: str):
        """
        Generator: streamuje tokeny z Ollama jeden po druhém.
        Přidá user zprávu do historie; assistant přidá volající kód
        po získání plné odpovědi přes _parse_response.
        """
        self.history.append({"role": "user", "content": user_text})
        self._stream_resp = None

        payload = {
            "model":    self.model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                         *list(self.history)],
            "stream":   True,
            "options":  {"temperature": 0.1, "num_predict": 500},
        }

        try:
            self._stream_resp = requests.post(
                self.url, json=payload, stream=True, timeout=60
            )
            self._stream_resp.raise_for_status()

            for line in self._stream_resp.iter_lines():
                if not line:
                    continue
                try:
                    data  = json.loads(line.decode("utf-8"))
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        yield chunk
                    if data.get("done"):
                        break
                except json.JSONDecodeError:
                    continue

        except Exception as e:
            logger.error(f"Stream chyba: {e}")
            yield f"Chyba: {e}"
        finally:
            self._stream_resp = None

    def drain_stream(self):
        """Dočerpá zbytek streamu po přerušení (COMMAND detekce)"""
        if self._stream_resp is None:
            return
        try:
            for line in self._stream_resp.iter_lines():
                if not line:
                    continue
                try:
                    data  = json.loads(line.decode("utf-8"))
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        yield chunk
                    if data.get("done"):
                        break
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass
        finally:
            self._stream_resp = None

    def clear_history(self):
        self.history.clear()
        logger.info("Historie vymazána")

    def is_available(self) -> bool:
        try:
            resp = requests.get(
                self.url.replace("/api/chat", "/api/tags"), timeout=3
            )
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                return any(self.model in m for m in models)
        except Exception:
            pass
        return False
