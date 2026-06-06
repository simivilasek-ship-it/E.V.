"""Auto-migrated from dashboard.py — config routes."""
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

    @app.get("/api/profile")
    async def get_profile():
        """Vrátí základní user profile pro Hero panel (jméno, fakta)."""
        try:
            from user_profile import get_user_profile
            from config import CONFIG, __version__
            profile = get_user_profile()
            name  = profile.get("jméno") or profile.get("name") or ""
            facts = {f.key: f.value for f in profile.all_facts()} if hasattr(profile, "all_facts") else {}
            model = CONFIG.get("ollama_model", "?")
            return {
                "name":    name,
                "facts":   facts,
                "model":   model,
                "version": __version__,
            }
        except Exception:
            return {"name": "", "facts": {}, "model": "?", "version": "4.5"}

    @app.get("/api/config")
    async def get_config():
        """Vrátí aktuální konfiguraci (bez secrets)."""
        try:
            from config import CONFIG
            safe = {k: v for k, v in CONFIG.items()
                    if k not in ("brave_api_key",) and "key" not in k.lower()}
            return safe
        except Exception:
            return {}

    @app.get("/api/debug/bundle")
    async def debug_bundle(limit_log_lines: int = 400):
        """Vytvoří ZIP bundle pro bugreport (bez secrets)."""
        import io, json, os, platform, zipfile, time
        from pathlib import Path as _Path
        from fastapi.responses import StreamingResponse

        limit = max(50, min(int(limit_log_lines or 400), 2000))
        root = ROOT

        # Safe config
        try:
            from config import CONFIG, __version__
            safe_config = {k: v for k, v in CONFIG.items()
                           if k not in ("brave_api_key",) and "key" not in k.lower()}
        except Exception:
            __version__ = "unknown"
            safe_config = {}

        meta = {
            "timestamp": int(time.time()),
            "version": __version__,
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "python": platform.python_version(),
            },
            "env": {
                "JARVIS_HEADLESS": os.getenv("JARVIS_HEADLESS", ""),
                "AUTO_RELOAD": os.getenv("AUTO_RELOAD", ""),
                "DEBUG_MODE": os.getenv("DEBUG_MODE", ""),
            },
        }

        def _tail_text(path: _Path) -> str:
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                return "\n".join(lines[-limit:])
            except Exception:
                return ""

        # Collect logs if present (never include .env)
        log_text = _tail_text(root / "jarvis.log")
        audit_text = _tail_text(root / "audit.log")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("meta.json", json.dumps(meta, ensure_ascii=False, indent=2))
            zf.writestr("config.safe.json", json.dumps(safe_config, ensure_ascii=False, indent=2))
            if log_text:
                zf.writestr("jarvis.log.tail.txt", log_text)
            if audit_text:
                zf.writestr("audit.log.tail.txt", audit_text)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=jarvis-debug-bundle.zip"},
        )

    @app.post("/api/config")
    async def update_config(body: dict):
        """Aktualizuje konfiguraci za běhu (whitelist bezpečných klíčů)."""
        ALLOWED = {
            # LLM
            "ollama_model", "history_size",
            # TTS
            "tts_enabled", "tts_voice", "tts_rate", "tts_streaming",
            # STT
            "stt_language", "stt_energy_threshold", "stt_timeout", "stt_phrase_limit",
            # Wake word
            "wake_word", "wake_word_enabled",
            # Agent
            "agent_max_steps", "agent_timeout",
            # MCP toggles
            "mcp_filesystem_enabled", "mcp_git_enabled", "mcp_memory_enabled",
            "mcp_fetch_enabled", "mcp_brave_enabled", "mcp_playwright_enabled",
            "mcp_github_enabled", "mcp_youtube_transcript_enabled",
            "mcp_google_maps_enabled", "mcp_slack_enabled",
            "mcp_sequential_thinking_enabled", "mcp_puppeteer_enabled",
            "mcp_computer_control_enabled", "mcp_time_enabled",
        }
        try:
            from config import CONFIG, save_config
            changed = {}
            for k, v in body.items():
                if k in ALLOWED:
                    CONFIG[k] = v
                    changed[k] = v
            if changed:
                save_config(CONFIG)
            return {"updated": changed, "ok": True}
        except Exception as e:
            return {"error": str(e), "ok": False}


