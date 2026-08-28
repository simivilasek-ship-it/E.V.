"""E.V. → Cursor agent. Řekneš E.V., ona předá práci Cursora v projektu."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_STATE_PATH = Path.home() / ".jarvis" / "cursor_agent.json"

_TRIGGER_NORM = re.compile(
    r"(?:"
    r"rekni(?:\s+to)?\s+(?:cursoru|kurzoru|kursoru)(?:\s+at)?|"
    r"posli(?:\s+to)?\s+(?:cursoru|kurzoru|kursoru)|"
    r"predej(?:\s+to)?\s+(?:cursoru|kurzoru|kursoru)|"
    r"spoj(?:\s+se)?\s+(?:prosim\s+)?s\s+(?:cursorem?|kurzorem?|kursorem?)|"
    r"cursorovi|kurzorovi|kursorovi|"
    r"at(?:\s+to)?\s+(?:cursor|kurzor|kursor)(?:u)?"
    r")",
    re.I,
)

_TRIGGER_STRIP = re.compile(
    r"^\s*(?:"
    r"[rřRŘ]ekni(?:\s+to)?\s+(?:[cC]ursoru|[kK]urzoru|[kK]ursoru)(?:\s+a[tťTŤ])?|"
    r"po[sšSŠ]li(?:\s+to)?\s+(?:[cC]ursoru|[kK]urzoru|[kK]ursoru)|"
    r"p[rřRŘ]edej(?:\s+to)?\s+(?:[cC]ursoru|[kK]urzoru|[kK]ursoru)|"
    r"[sS]poj(?:\s+se)?\s+(?:prosím\s+|prosim\s+)?s\s+(?:[cC]ursorem?|[kK]urzorem?|[kK]ursorem?)|"
    r"(?:[cC]ursorovi|[kK]urzorovi|[kK]ursorovi)\s*:?|"
    r"a[tťTŤ](?:\s+to)?\s+(?:[cC]ursor|[kK]urzor|[kK]ursor)(?:u)?"
    r")\s*[,:]?\s*",
)

_CODE_HINT = re.compile(
    r"\b("
    r"oprav|bug|refaktor|commit|pull\s*request|soubor|funkci|test|"
    r"implementuj|prepis|typescript|python|komponent|projekt|"
    r"pridej|kod|kód|refactor"
    r")\b",
    re.I,
)


def cursor_api_key(config: Optional[dict] = None) -> str:
    cfg = config or {}
    return (
        str(cfg.get("cursor_api_key") or "").strip()
        or __import__("os").environ.get("CURSOR_API_KEY", "").strip()
    )


def cursor_configured(config: Optional[dict] = None) -> bool:
    return bool(cursor_api_key(config))


def extract_cursor_prompt(text: str, normalized: str = "") -> Optional[str]:
    """Vrátí zadání pro Cursor, nebo None když to nemá jít do Cursora."""
    raw = (text or "").strip()
    t = (normalized or raw).strip()
    if not raw:
        return None
    if _TRIGGER_NORM.search(t):
        rest = _TRIGGER_STRIP.sub("", raw, count=1).strip(" .,!")
        if rest == raw.strip(" .,!"):
            rest = _TRIGGER_NORM.sub("", t, count=1).strip(" .,!")
            rest = re.sub(r"^(at|a)\s+", "", rest, flags=re.I).strip(" .,!")
        return rest
    if cursor_process_running() and _CODE_HINT.search(t):
        return raw
    return None


def cursor_process_running() -> bool:
    try:
        import psutil

        for proc in psutil.process_iter(["name"]):
            name = (proc.info.get("name") or "").lower()
            if name == "cursor" or name.startswith("cursor"):
                return True
    except Exception:
        return False
    return False


def resolve_workspace(config: Optional[dict] = None) -> Path:
    cfg = config or {}
    pinned = str(cfg.get("cursor_workspace") or "").strip()
    if pinned:
        path = Path(pinned).expanduser()
        if path.is_dir():
            return path
    from_proc = _workspace_from_cursor_process()
    if from_proc is not None:
        return from_proc
    try:
        from src.api.paths import ROOT

        if ROOT.is_dir():
            return ROOT
    except Exception:
        pass
    return Path.cwd()


def _looks_like_project(path: Path) -> bool:
    return (
        (path / ".git").is_dir()
        or (path / "package.json").is_file()
        or (path / "pyproject.toml").is_file()
        or (path / "requirements.txt").is_file()
    )


def _workspace_from_cursor_process() -> Optional[Path]:
    try:
        import psutil
    except Exception:
        return None
    seen: set[str] = set()
    for proc in psutil.process_iter(["name", "cwd"]):
        name = (proc.info.get("name") or "").lower()
        if not (name == "cursor" or name.startswith("cursor")):
            continue
        cwd = proc.info.get("cwd") or ""
        if not cwd or cwd in seen:
            continue
        seen.add(cwd)
        path = Path(cwd)
        low = str(path).lower()
        if "cursor" in low and any(part in low for part in ("resources", "usr/share", "appimage")):
            continue
        if _looks_like_project(path):
            return path
        parent = path.parent
        if _looks_like_project(parent):
            return parent
    return None


def _load_agent_id(workspace: Path) -> str:
    try:
        data = json.loads(_STATE_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return str(data.get(str(workspace)) or "").strip()
    except Exception:
        return ""
    return ""


def _save_agent_id(workspace: Path, agent_id: str) -> None:
    data: dict = {}
    try:
        if _STATE_PATH.exists():
            loaded = json.loads(_STATE_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
    except Exception:
        data = {}
    data[str(workspace)] = agent_id
    try:
        _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _STATE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.debug("cursor_bridge: nelze uložit agent id: %s", e)


def _wrap_prompt(prompt: str) -> str:
    return (
        "Uživatel to řekl E.V. nahlas. Ty jsi Cursor agent v tomhle projektu.\n\n"
        f"{prompt.strip()}\n\n"
        "Udělej to. Na konci napiš krátké shrnutí česky, dvě až čtyři věty, "
        "bez markdownu — E.V. to řekne nahlas."
    )


def _result_text(run, result) -> str:
    for attr in ("result", "text", "message"):
        value = getattr(result, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    try:
        text = run.text()
        if isinstance(text, str) and text.strip():
            return text.strip()
    except Exception:
        pass
    return ""


def ask_cursor(prompt: str, config: Optional[dict] = None) -> str:
    """Pošle zadání Cursor agentovi. Vrací text, který má E.V. říct."""
    spoken_task = (prompt or "").strip()
    if not spoken_task:
        return "Řekni, co mám Cursorovi předat."

    cfg = config
    if cfg is None:
        try:
            from config import CONFIG
            cfg = CONFIG
        except Exception:
            cfg = {}

    key = cursor_api_key(cfg)
    if not key:
        return (
            "K Cursora se nedostanu — chybí CURSOR_API_KEY. "
            "Přidej ho do .env z cursor.com/dashboard/integrations."
        )

    try:
        from cursor_sdk import Agent, AgentOptions, CursorAgentError, LocalAgentOptions
    except ImportError:
        return "Chybí balíček cursor-sdk. Nainstaluj ho do venv: pip install cursor-sdk."

    workspace = resolve_workspace(cfg)
    model = str(cfg.get("cursor_model") or "composer-2.5").strip() or "composer-2.5"
    wrapped = _wrap_prompt(spoken_task)
    options = AgentOptions(
        api_key=key,
        model=model,
        local=LocalAgentOptions(cwd=str(workspace)),
    )

    def _run_with(agent) -> str:
        agent_id = getattr(agent, "agent_id", "") or getattr(agent, "agentId", "")
        if agent_id:
            _save_agent_id(workspace, str(agent_id))
        run = agent.send(wrapped)
        result = run.wait()
        status = getattr(result, "status", "") or ""
        text = _result_text(run, result)
        if status == "error":
            return "Cursor to nedotáhl. Zkus to říct znovu, nebo se podívej do chatu v Cursora."
        if text:
            try:
                from tts import prepare_speech_text

                return prepare_speech_text(text, limit=420)
            except Exception:
                return text[:420]
        return "Hotovo. Mrkni do Cursora, změny už tam jsou."

    try:
        previous = _load_agent_id(workspace)
        if previous:
            try:
                with Agent.resume(previous, options) as agent:
                    return _run_with(agent)
            except CursorAgentError as err:
                logger.info("Cursor resume selhal (%s), zakládám nového", err)
        with Agent.create(
            model=model,
            api_key=key,
            local=LocalAgentOptions(cwd=str(workspace)),
        ) as agent:
            return _run_with(agent)
    except CursorAgentError as err:
        retry = getattr(err, "is_retryable", False)
        extra = " Zkusím to znovu za chvíli." if retry else ""
        return f"Cursor se nespustil: {err}.{extra}".replace("..", ".")
    except Exception as e:
        logger.exception("ask_cursor")
        return f"Spojení s Cursorem selhalo: {e}"
