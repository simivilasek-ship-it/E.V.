"""Auto-migrated from dashboard.py — skills routes."""
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

    # ── Skill Generator ───────────────────────────────

    @app.post("/api/skill/generate")
    async def skill_generate(body: dict):
        """Vygeneruje plugin skeleton z přirozeného popisu."""
        prompt = body.get("prompt", "").strip()
        if not prompt:
            return {"error": "Prázdný prompt"}
        try:
            from llm import OllamaClient
            from config import CONFIG
            client = OllamaClient(CONFIG["ollama_url"], CONFIG["ollama_model"])

            system = """\
    Jsi expert na tvorbu JARVIS pluginů. Vygeneruj funkční plugin pro zadaný účel.

    Plugin se skládá ze dvou souborů:
    1. skill.py — Python kód
    2. manifest.json — metadata

    FORMÁT ODPOVĚDI (jen JSON, nic jiného):
    {
  "name": "nazev_pluginu",
  "description": "Co plugin dělá",
  "triggers": ["klíčové slovo 1", "klíčové slovo 2"],
  "permissions": ["answer"],
  "skill_py": "import re\\n...celý kód skill.py...",
  "manifest": {"name":"...","version":"1.0.0","description":"...","permissions":["answer"],"triggers":["..."]}
    }

    Pravidla pro skill.py:
    - Importuj jen povolené moduly (requests, json, re, datetime, math, collections…)
    - Definuj _PATTERN = re.compile(r"\\b(trigger)\\b", re.IGNORECASE)
    - Definuj _handle(text: str) -> tuple[str, dict]
    - Vrať (zpráva, {"action": "answer", "params": {}})
    - def get_routes(): return [{"pattern": _PATTERN, "handler": _handle}]
    - def get_actions(): return {}
    """
            result = client.call_json(
                [{"role": "system", "content": system},
                 {"role": "user", "content": f"Vytvoř plugin: {prompt}"}],
                temperature=0.3, max_tokens=1200,
            )
            if not result or "skill_py" not in result:
                return {"error": "LLM nevrátil validní JSON — zkus znovu nebo uprosti prompt"}
            # Validace syntaxe vygenerovaného kódu
            import ast as _ast
            try:
                _ast.parse(result["skill_py"])
            except SyntaxError as se:
                return {
                    "error": f"Syntaktická chyba v generovaném kódu (řádek {se.lineno}): {se.msg}",
                    "hint": "Zkus prompt přeformulovat nebo zjednodušit",
                    "raw": result,
                }
            # Ověř přítomnost povinných funkcí
            tree = _ast.parse(result["skill_py"])
            fns = {n.name for n in _ast.walk(tree) if isinstance(n, _ast.FunctionDef)}
            missing = {"get_routes", "get_actions"} - fns
            if missing:
                result["warning"] = f"Chybí funkce: {', '.join(missing)} — plugin nemusí fungovat"
            return result
        except Exception as e:
            return {"error": str(e)}

    @app.post("/api/skill/save")
    async def skill_save(body: dict):
        """Uloží vygenerovaný plugin do plugins/custom/."""
        import re as _re
        name       = body.get("name", "").strip().replace(" ", "_").lower()
        skill_code = body.get("skill_code", "")
        manifest   = body.get("manifest", {})
        if not name or not skill_code:
            return {"error": "Chybí name nebo skill_code"}
        if not _re.fullmatch(r"[a-z0-9_\\-]{1,64}", name):
            return {"error": "Neplatný název pluginu (povoleno: a-z, 0-9, _, -; max 64 znaků)"}
        try:
            from pathlib import Path as _Path
            root = ROOT
            base = (root / "plugins" / "custom").resolve()
            dest = (base / name).resolve()
            if base not in dest.parents:
                return {"error": "Neplatná cesta pro plugin (path traversal blocked)"}
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "skill.py").write_text(skill_code, encoding="utf-8")
            import json as _json
            if manifest:
                (dest / "manifest.json").write_text(
                    _json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            try:
                from plugin_system import get_plugin_system
                ps = get_plugin_system()
                if ps:
                    ps.reload_plugin(name)
            except Exception:
                pass
            return {"saved": str(dest), "name": name}
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/skill/download/{name}")
    async def skill_download(name: str):
        """Stáhne plugin jako ZIP archiv."""
        import re as _re
        if not _re.fullmatch(r"[a-z0-9_\\-]{1,64}", name):
            from fastapi import HTTPException
            raise HTTPException(400, "Neplatný název pluginu")
        import zipfile, io
        from fastapi.responses import StreamingResponse
        from pathlib import Path as _Path
        dest = ROOT / "plugins" / "custom" / name
        if not dest.exists():
            from fastapi import HTTPException
            raise HTTPException(404, f"Plugin '{name}' nenalezen")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in dest.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(dest.parent))
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={name}.zip"},
        )


