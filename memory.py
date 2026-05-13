"""
JARVIS v3.0 — Neural Memory System + Daily Summarizer
Integrovaný brain-inspired memory layer pro JARVIS.
DailySummarizer extrahuje fakta z dnešních konverzací a ukládá do UserProfile.
"""

from __future__ import annotations
import os
import json
import logging
import threading
import time
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional

try:
    from neural_memory import MemorySystem, MemoryConfig, LifecycleConfig, RetrievalWeights
    from neural_memory.providers import LocalProvider
    HAS_NEURAL_MEMORY = True
except ImportError:
    HAS_NEURAL_MEMORY = False
    MemorySystem = None

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════
#  VESTAVĚNÁ JSON PAMĚŤ (fallback — bez závislostí)
# ══════════════════════════════════════════════════════

import uuid
import math as _math


class _JSONMemoryStore:
    """
    Jednoduchá persistentní paměť v JSON.
    Funguje vždy — bez externích závislostí.
    Keyword-based recall (TF-IDF aproximace přes word overlap).
    """

    def __init__(self, path: Path):
        self._path = path
        self._path.mkdir(parents=True, exist_ok=True)
        self._file = self._path / "memories.json"
        self._lock = threading.Lock()
        self._data: List[dict] = []
        self._load()

    def _load(self) -> None:
        try:
            if self._file.exists():
                self._data = json.loads(self._file.read_text(encoding="utf-8"))
        except Exception:
            self._data = []

    def _save(self) -> None:
        try:
            self._file.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"JSON memory save chyba: {e}")

    def store(self, content: str, importance: float, tags: List[str],
              metadata: dict) -> str:
        mid = str(uuid.uuid4())[:8]
        entry = {
            "id": mid,
            "content": content,
            "importance": importance,
            "tags": tags,
            "metadata": metadata,
            "created_at": time.time(),
            "last_access": time.time(),
            "access_count": 0,
        }
        with self._lock:
            self._data.append(entry)
            self._save()
        return mid

    def recall(self, query: str, top_k: int, min_importance: float) -> List[dict]:
        q_words = set(query.lower().split())
        results = []
        with self._lock:
            for entry in self._data:
                if entry["importance"] < min_importance:
                    continue
                c_words = set(entry["content"].lower().split())
                overlap = len(q_words & c_words)
                if overlap == 0:
                    continue
                # Recency bonus: půlnoc 14 dní
                age_days = (time.time() - entry["created_at"]) / 86400
                recency = _math.exp(-age_days / 14)
                score = 0.5 * (overlap / max(len(q_words), 1)) + \
                        0.3 * entry["importance"] + \
                        0.2 * recency
                results.append({**entry, "_score": score})
        results.sort(key=lambda x: x["_score"], reverse=True)
        # Aktualizuj last_access
        ids = {r["id"] for r in results[:top_k]}
        with self._lock:
            for e in self._data:
                if e["id"] in ids:
                    e["last_access"] = time.time()
                    e["access_count"] += 1
            if ids:
                self._save()
        return results[:top_k]

    def forget(self, mid: str) -> bool:
        with self._lock:
            before = len(self._data)
            self._data = [e for e in self._data if e["id"] != mid]
            changed = len(self._data) < before
            if changed:
                self._save()
        return changed

    def maintenance(self, decay_rate: float = 0.01,
                    min_importance: float = 0.05) -> dict:
        """Sníží importance starých vzpomínek, odstraní pod prahem."""
        removed = 0
        with self._lock:
            for entry in self._data:
                age_days = (time.time() - entry["created_at"]) / 86400
                entry["importance"] *= _math.exp(-decay_rate * age_days)
            before = len(self._data)
            self._data = [e for e in self._data
                          if e["importance"] >= min_importance]
            removed = before - len(self._data)
            self._save()
        logger.info(f"Memory maintenance: odstraněno {removed} vzpomínek")
        return {"removed": removed, "remaining": len(self._data)}

    def stats(self) -> dict:
        with self._lock:
            total = len(self._data)
            avg_imp = sum(e["importance"] for e in self._data) / total if total else 0.0
        return {"total_memories": total, "avg_importance": round(avg_imp, 3)}


# ══════════════════════════════════════════════════════
#  JARVIS MEMORY (unifikovaná fasáda)
# ══════════════════════════════════════════════════════

class JarvisMemory:
    """
    Paměťová fasáda pro JARVIS.
    Preferuje neural-ai-memory pokud je nainstalovaná,
    jinak používá vestavěný JSON store (vždy funkční).
    """

    def __init__(self, config: dict):
        self.config = config
        mem_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "memory_data"

        if HAS_NEURAL_MEMORY:
            try:
                mem_cfg = MemoryConfig(
                    persist_directory=str(mem_dir),
                    retrieval=RetrievalWeights(relevance=0.4, importance=0.4, recency=0.2),
                    lifecycle=LifecycleConfig(
                        decay_rate=0.02, decay_threshold=0.1,
                        merge_similarity_threshold=0.85,
                        abstraction_cluster_size=3,
                        auto_maintenance_interval=20,
                    ),
                    use_llm_importance_scoring=False,
                    recency_half_life_days=14.0,
                )
                self.system = MemorySystem(provider=LocalProvider(), config=mem_cfg)
                self._store: Optional[_JSONMemoryStore] = None
                logger.info(f"Neural memory inicializován v: {mem_dir}")
                return
            except Exception as e:
                logger.warning(f"Neural memory init selhal: {e}, používám JSON fallback")

        self.system = None
        self._store = _JSONMemoryStore(mem_dir)
        logger.info(f"JSON memory inicializován v: {mem_dir}")

    # ── Store ──────────────────────────────────────────

    def store(self, content: str, importance: float = 0.5, context: str = None,
              tags: List[str] = None, metadata: dict = None) -> Optional[str]:
        if self.system:
            try:
                mem = self.system.store(content=content, importance=importance,
                                        context=context, tags=tags or [],
                                        metadata=metadata or {})
                return mem.id
            except Exception as e:
                logger.error(f"Neural memory store chyba: {e}")
                return None
        return self._store.store(content, importance, tags or [], metadata or {})

    # ── Recall ─────────────────────────────────────────

    def recall(self, query: str, top_k: int = 5,
               min_importance: float = 0.0) -> List[dict]:
        if self.system:
            try:
                results = self.system.recall(query=query, top_k=top_k,
                                             min_importance=min_importance)
                return [{
                    "content": r.memory.content,
                    "importance": r.memory.importance,
                    "score": r.final_score,
                    "tags": r.memory.tags,
                    "metadata": r.memory.metadata,
                    "created_at": r.memory.created_at.isoformat() if r.memory.created_at else None,
                } for r in results]
            except Exception as e:
                logger.error(f"Neural memory recall chyba: {e}")
                return []
        return self._store.recall(query, top_k, min_importance)

    # ── Forget ─────────────────────────────────────────

    def forget(self, memory_id: str) -> bool:
        if self.system:
            try:
                self.system.forget(memory_id)
                return True
            except Exception as e:
                logger.error(f"Neural memory forget chyba: {e}")
                return False
        return self._store.forget(memory_id)

    # ── Maintenance ────────────────────────────────────

    def run_maintenance(self) -> dict:
        if self.system:
            try:
                return self.system.run_maintenance()
            except Exception as e:
                return {"error": str(e)}
        return self._store.maintenance()

    # ── Stats ──────────────────────────────────────────

    def stats(self) -> dict:
        if self.system:
            try:
                s = self.system.stats()
                return {
                    "total_memories": s.total_memories,
                    "avg_importance": s.avg_importance,
                    "by_category": dict(s.by_category) if s.by_category else {},
                }
            except Exception as e:
                return {"error": str(e)}
        return self._store.stats()

    def store_conversation(self, user_message: str, ai_response: str, importance: float = 0.3):
        """Uloží konverzační pár"""
        content = f"User: {user_message}\nAI: {ai_response}"
        self.store(
            content=content,
            importance=importance,
            tags=["conversation"],
            metadata={"type": "conversation", "user": user_message[:100]}
        )

    def recall_context(self, current_query: str, top_k: int = 3) -> str:
        """Získá kontext z paměti pro aktuální dotaz."""
        memories = self.recall(current_query, top_k=top_k, min_importance=0.2)
        if not memories:
            return ""
        parts = []
        for mem in memories:
            if mem["tags"] and "conversation" in mem["tags"]:
                parts.append(f"Previous: {mem['content']}")
            else:
                parts.append(f"Memory: {mem['content']}")
        context = "\n".join(parts)
        logger.info(f"Kontext z paměti: {len(context)} znaků")
        return context


# ══════════════════════════════════════════════════════
#  DAILY SUMMARIZER
# ══════════════════════════════════════════════════════

class DailySummarizer:
    """
    Každou půlnoc (nebo on-demand) vezme dnešní konverzace,
    pošle je do Ollama, extrahuje fakta o uživateli a uloží do UserProfile.
    Výsledek shrnutí se uloží do memory s tag "daily_summary".
    """

    def __init__(self, config: dict, memory: JarvisMemory):
        self.config = config
        self.memory = memory
        self._state_file = Path.home() / ".jarvis_daily_summary.json"
        self._lock = threading.Lock()

    def _last_summary_date(self) -> Optional[date]:
        try:
            if self._state_file.exists():
                data = json.loads(self._state_file.read_text())
                return date.fromisoformat(data.get("last_date", ""))
        except Exception:
            pass
        return None

    def _save_last_date(self, d: date) -> None:
        try:
            self._state_file.write_text(
                json.dumps({"last_date": d.isoformat()}), encoding="utf-8")
        except Exception:
            pass

    def should_run(self) -> bool:
        """True pokud dnes ještě neproběhlo shrnutí."""
        last = self._last_summary_date()
        return last is None or last < date.today()

    def run(self, force: bool = False) -> str:
        """Spustí denní shrnutí. Vrátí text shrnutí nebo '' pokud nespuštěno."""
        if not force and not self.should_run():
            return ""

        with self._lock:
            try:
                return self._do_summarize()
            except Exception as e:
                logger.error(f"DailySummarizer chyba: {e}")
                return ""

    def _do_summarize(self) -> str:
        from user_profile import get_user_profile
        import requests as _req

        # Získej dnešní konverzace z memory (query = "dnešní konverzace")
        today_mems = self.memory.recall(
            "dnešní konverzace rozhovor",
            top_k=20,
            min_importance=0.0,
        )
        if not today_mems:
            logger.info("DailySummarizer: žádné konverzace ke shrnutí")
            self._save_last_date(date.today())
            return ""

        # Sestav konverzační blok
        conv_text = "\n".join(m["content"] for m in today_mems[:15])[:3000]

        prompt = f"""Analyzuj níže uvedené konverzace s AI asistentem a extrahuj:
1. Fakta o uživateli (jméno, město, profese, zájmy, preference)
2. Témata, o která se zajímá
3. Problémy které řeší

Odpověz ve formátu JSON:
{{
  "fakta": {{"jméno": "...", "město": "...", "zájmy": [...]}},
  "témata": ["...", "..."],
  "shrnutí": "Krátké shrnutí dne v 1-2 větách."
}}

Konverzace:
{conv_text}"""

        try:
            r = _req.post(
                self.config.get("ollama_url", "http://localhost:11434/api/chat"),
                json={
                    "model": self.config.get("ollama_model", "qwen2.5:3b"),
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 600},
                },
                timeout=60,
            )
            r.raise_for_status()
            content = r.json().get("message", {}).get("content", "").strip()

            # Parsuj JSON z odpovědi
            import re
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                profile = get_user_profile()

                # Ulož fakta do UserProfile
                for key, value in data.get("fakta", {}).items():
                    if value:
                        profile.set(key, value, confidence=0.7, source="daily_summary")

                # Extrahuj zájmy z témat
                for tema in data.get("témata", []):
                    existing = profile.get("zájmy") or []
                    if isinstance(existing, list) and tema not in existing:
                        existing.append(tema)
                        profile.set("zájmy", existing, confidence=0.5, source="inferred")

                summary_text = data.get("shrnutí", "")
            else:
                summary_text = content[:200]

            # Ulož shrnutí do memory s vysokou důležitostí
            if summary_text:
                self.memory.store(
                    content=f"Denní shrnutí {date.today()}: {summary_text}",
                    importance=0.9,
                    tags=["daily_summary", str(date.today())],
                )

            self._save_last_date(date.today())
            logger.info(f"DailySummarizer: hotovo — {summary_text[:80]}")
            return summary_text

        except Exception as e:
            logger.error(f"DailySummarizer LLM chyba: {e}")
            self._save_last_date(date.today())
            return ""

    def schedule_midnight(self, scheduler) -> None:
        """Naplánuje spuštění denního shrnutí každou půlnoc."""
        scheduler.every_day_at(0, 5, lambda: self.run())
        logger.info("DailySummarizer naplánován na 00:05")