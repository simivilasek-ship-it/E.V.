"""E.V. Proaktivní návrhy API"""
from __future__ import annotations
import psutil
from fastapi import APIRouter

router = APIRouter(prefix="/api/proactive", tags=["proactive"])

@router.get("/suggestions")
async def get_suggestions():
    """Vrátí proaktivní návrhy na základě aktuálního stavu systému."""
    try:
        from src.predictive_engine import PredictiveEngine
        
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        ram_pct = mem.percent
        ram_avail_mb = mem.available / 1024 / 1024
        
        # Aktivní aplikace (jen názvy procesů)
        try:
            active = [p.name() for p in psutil.process_iter(['name']) if p.info['name']][:20]
        except Exception:
            active = []
        
        engine = PredictiveEngine()
        suggestions = engine.get_suggestions(active, cpu, ram_pct, ram_avail_mb)
        return {"ok": True, "suggestions": suggestions, "cpu": cpu, "ram_pct": ram_pct}
    except Exception as e:
        return {"ok": False, "suggestions": [], "error": str(e)}
