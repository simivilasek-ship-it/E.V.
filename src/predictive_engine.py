"""
E.V. Predictive Intelligence Engine
Sleduje vzory chování a předpovídá potřeby uživatele.
"""
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)
_STATE_FILE = Path.home() / ".jarvis" / "predictive_state.json"

class PredictiveEngine:
    """Analyzuje vzory chování a generuje proaktivní návrhy."""
    
    def __init__(self):
        self._state = self._load_state()
    
    def _load_state(self) -> dict:
        try:
            if _STATE_FILE.exists():
                return json.loads(_STATE_FILE.read_text())
        except Exception:
            pass
        return {"app_patterns": {}, "time_patterns": {}, "last_suggestions": []}
    
    def _save_state(self):
        try:
            _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            _STATE_FILE.write_text(json.dumps(self._state, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.warning("Nelze uložit stav: %s", e)
    
    def record_app_open(self, app_name: str):
        """Zaznamenej otevření aplikace."""
        patterns = self._state["app_patterns"]
        if app_name not in patterns:
            patterns[app_name] = {"count": 0, "co_opened": {}}
        patterns[app_name]["count"] += 1
        self._save_state()
    
    def get_suggestions(self, active_apps: list[str], cpu_pct: float, ram_pct: float, ram_available_mb: float) -> list[str]:
        """Vrátí seznam proaktivních návrhů."""
        suggestions = []
        hour = datetime.now().hour
        
        # RAM predikce
        if ram_pct > 85:
            suggestions.append(f"⚠️ RAM na {ram_pct:.0f}% — doporučuji zavřít nepotřebné aplikace.")
        elif ram_pct > 70:
            suggestions.append(f"RAM na {ram_pct:.0f}%. Sleduju trend.")
        
        # CPU predikce
        if cpu_pct > 90:
            suggestions.append(f"🔥 CPU na {cpu_pct:.0f}% — systém je pod zátěží.")
        
        # Čas
        if hour >= 22:
            suggestions.append("🌙 Je po 22:00. Nezapomeň commitu a ulož práci.")
        elif hour < 7:
            suggestions.append("🌅 Ranní startup. Systémy E.V. připraveny.")
        
        # App patterns — detekce VSCode + Docker
        vscode_open = any("code" in a.lower() or "vscode" in a.lower() for a in active_apps)
        docker_open = any("docker" in a.lower() for a in active_apps)
        if vscode_open and docker_open:
            suggestions.append("💡 Detekuji VSCode + Docker. Chceš připravit dev workspace?")
        
        return suggestions[:3]  # Max 3 návrhy najednou
