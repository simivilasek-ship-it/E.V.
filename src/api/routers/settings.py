"""Auto-migrated from dashboard.py — settings routes."""
from __future__ import annotations

import asyncio
import json
import time

import psutil

from src.api.deps import (
    HAS_LOGURU,
    __version__,
    get_scheduler,
    get_security_manager,
    logger,
    logger_module_available,
    start_time,
)
from src.api.paths import ROOT
from src.api.ws import (
    confirm_mgr,
    graph_clients,
    graph_mgr,
    ws_clients,
    ws_mgr,
)

if logger_module_available:
    pass  # imports satisfied above
else:
    def get_scheduler():  # type: ignore
        raise RuntimeError("scheduler unavailable")

    def get_security_manager():  # type: ignore
        raise RuntimeError("security unavailable")


def register(app):

    @app.get("/api/models")
    async def list_models():
        """Vrátí dostupné Ollama modely."""
        try:
            import requests as _r
            from config import CONFIG
            base = CONFIG.get("ollama_url", "http://localhost:11434/api/chat")
            r = _r.get(base.replace("/api/chat", "/api/tags"), timeout=4)
            if r.status_code == 200:
                return {"models": [m["name"] for m in r.json().get("models", [])]}
        except Exception:
            pass
        return {"models": []}

    @app.get("/api/settings")
    async def get_settings():
        """Vrátí aktuální nastavení + metadata (min/max/options) pro Settings UI."""
        import shutil as _shutil
        try:
            from config import CONFIG
        except ImportError:
            return {"error": "config modul není dostupný"}

        # Dostupné Ollama modely
        available_models: list = []
        try:
            import requests as _r
            base = CONFIG.get("ollama_url", "http://localhost:11434/api/chat")
            r = _r.get(base.replace("/api/chat", "/api/tags"), timeout=3)
            if r.status_code == 200:
                available_models = [m["name"] for m in r.json().get("models", [])]
        except Exception:
            pass

        # MCP servery — statická tabulka (command + config key)
        _MCP_SERVERS = [
            ("filesystem",           "npx",  "mcp_filesystem_enabled"),
            ("git",                  "uvx",  "mcp_git_enabled"),
            ("mcp-memory",           "npx",  "mcp_memory_enabled"),
            ("fetch",                "uvx",  "mcp_fetch_enabled"),
            ("brave-search",         "npx",  "mcp_brave_enabled"),
            ("playwright",           "npx",  "mcp_playwright_enabled"),
            ("github",               "npx",  "mcp_github_enabled"),
            ("youtube-transcript",   "npx",  "mcp_youtube_transcript_enabled"),
            ("google-maps",          "npx",  "mcp_google_maps_enabled"),
            ("slack",                "npx",  "mcp_slack_enabled"),
            ("sequential-thinking",  "npx",  "mcp_sequential_thinking_enabled"),
            ("puppeteer",            "npx",  "mcp_puppeteer_enabled"),
            ("computer-control",     "uvx",  "mcp_computer_control_enabled"),
            ("time",                 "uvx",  "mcp_time_enabled"),
        ]
        mcp_status_map = {}
        for srv_name, cmd, cfg_key in _MCP_SERVERS:
            mcp_status_map[srv_name] = {
                "enabled": bool(CONFIG.get(cfg_key, True)),
                "command_found": _shutil.which(cmd) is not None,
            }

        return {
            "llm": {
                "model":            CONFIG.get("ollama_model", ""),
                "available_models": available_models,
                "history_size":     CONFIG.get("history_size", 20),
            },
            "tts": {
                "enabled":   CONFIG.get("tts_enabled", True),
                "voice":     CONFIG.get("tts_voice", ""),
                "rate":      CONFIG.get("tts_rate", "+0%"),
                "streaming": CONFIG.get("tts_streaming", True),
            },
            "stt": {
                "language":         CONFIG.get("stt_language", "cs-CZ"),
                "energy_threshold": CONFIG.get("stt_energy_threshold", 300),
                "timeout":          CONFIG.get("stt_timeout", 5),
                "phrase_limit":     CONFIG.get("stt_phrase_limit", 10),
            },
            "wake_word": {
                "enabled": CONFIG.get("wake_word_enabled", True),
                "word":    CONFIG.get("wake_word", "jarvis"),
            },
            "agent": {
                "max_steps": CONFIG.get("agent_max_steps", 10),
                "timeout":   CONFIG.get("agent_timeout", 60),
            },
            "mcp": mcp_status_map,
        }

    @app.get("/api/tts/voices")
    async def list_tts_voices():
        """Seznam dostupných edge-tts hlasů (filtrovano na cs-CZ + en-US/en-GB)."""
        import subprocess as _sub
        voices: list = []
        try:
            r = _sub.run(
                ["edge-tts", "--list-voices"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                for line in r.stdout.splitlines():
                    line = line.strip()
                    if not line or line.startswith("Name"):
                        continue
                    # Formát: "Name: cs-CZ-AntoninNeural, Gender: Male, Locale: cs-CZ"
                    # nebo tabulátorem oddělené sloupce
                    parts = [p.strip() for p in line.replace(",", "\t").split("\t") if p.strip()]
                    name = locale = gender = ""
                    for p in parts:
                        if p.startswith("Name:"):
                            name = p.split(":", 1)[1].strip()
                        elif p.startswith("Gender:"):
                            gender = p.split(":", 1)[1].strip()
                        elif p.startswith("Locale:"):
                            locale = p.split(":", 1)[1].strip()
                    # Fallback: první část jako name pokud parsování selhalo
                    if not name and parts:
                        name = parts[0]
                    if not locale:
                        # Odhadni z name (cs-CZ-AntoninNeural → cs-CZ)
                        segments = name.split("-")
                        if len(segments) >= 2:
                            locale = "-".join(segments[:2])
                    # Filtr: cs-CZ nebo en-US nebo en-GB
                    if locale in ("cs-CZ", "en-US", "en-GB"):
                        voices.append({"name": name, "locale": locale, "gender": gender})
        except FileNotFoundError:
            return {"voices": [], "error": "edge-tts není nainstalován (pip install edge-tts)"}
        except Exception as e:
            return {"voices": [], "error": str(e)}
        return {"voices": voices}

    @app.get("/api/mcp/status")
    async def mcp_status():
        """Status všech MCP serverů: name, enabled, command_found."""
        import shutil as _shutil
        try:
            from config import CONFIG
        except ImportError:
            return {"servers": [], "error": "config modul není dostupný"}

        _MCP_SERVERS = [
            ("filesystem",           "npx",  "mcp_filesystem_enabled"),
            ("git",                  "uvx",  "mcp_git_enabled"),
            ("mcp-memory",           "npx",  "mcp_memory_enabled"),
            ("fetch",                "uvx",  "mcp_fetch_enabled"),
            ("brave-search",         "npx",  "mcp_brave_enabled"),
            ("playwright",           "npx",  "mcp_playwright_enabled"),
            ("github",               "npx",  "mcp_github_enabled"),
            ("youtube-transcript",   "npx",  "mcp_youtube_transcript_enabled"),
            ("google-maps",          "npx",  "mcp_google_maps_enabled"),
            ("slack",                "npx",  "mcp_slack_enabled"),
            ("sequential-thinking",  "npx",  "mcp_sequential_thinking_enabled"),
            ("puppeteer",            "npx",  "mcp_puppeteer_enabled"),
            ("computer-control",     "uvx",  "mcp_computer_control_enabled"),
            ("time",                 "uvx",  "mcp_time_enabled"),
        ]
        servers = []
        for srv_name, cmd, cfg_key in _MCP_SERVERS:
            servers.append({
                "name":          srv_name,
                "enabled":       bool(CONFIG.get(cfg_key, True)),
                "command_found": _shutil.which(cmd) is not None,
                "config_key":    cfg_key,
            })
        return {"servers": servers}

    @app.post("/api/mcp/toggle")
    async def mcp_toggle(body: dict):
        """Zapne/vypne MCP server: {server: "github", enabled: true}."""
        _CONFIG_KEY_MAP = {
            "filesystem":          "mcp_filesystem_enabled",
            "git":                 "mcp_git_enabled",
            "mcp-memory":          "mcp_memory_enabled",
            "fetch":               "mcp_fetch_enabled",
            "brave-search":        "mcp_brave_enabled",
            "playwright":          "mcp_playwright_enabled",
            "github":              "mcp_github_enabled",
            "youtube-transcript":  "mcp_youtube_transcript_enabled",
            "google-maps":         "mcp_google_maps_enabled",
            "slack":               "mcp_slack_enabled",
            "sequential-thinking": "mcp_sequential_thinking_enabled",
            "puppeteer":           "mcp_puppeteer_enabled",
            "computer-control":    "mcp_computer_control_enabled",
            "time":                "mcp_time_enabled",
        }
        server  = body.get("server", "").strip()
        enabled = body.get("enabled")
        if not server:
            return {"ok": False, "error": "Chybí pole 'server'"}
        if enabled is None:
            return {"ok": False, "error": "Chybí pole 'enabled'"}
        cfg_key = _CONFIG_KEY_MAP.get(server)
        if not cfg_key:
            return {"ok": False, "error": f"Neznámý MCP server: '{server}'"}
        try:
            from config import CONFIG, save_config
            CONFIG[cfg_key] = bool(enabled)
            save_config(CONFIG)
            return {"ok": True, "server": server, "enabled": bool(enabled), "config_key": cfg_key}
        except Exception as e:
            return {"ok": False, "error": str(e)}


