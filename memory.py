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

class JarvisMemory:
    """Neural memory systém pro JARVIS"""

    def __init__(self, config: dict):
        self.config = config
        self.memory_dir = os.path.join(os.path.dirname(__file__), "memory_data")

        if not HAS_NEURAL_MEMORY:
            logger.warning("neural-ai-memory není nainstalován. Používám fallback.")
            self.system = None
            return

        # Konfigurace pro JARVIS
        mem_config = MemoryConfig(
            persist_directory=self.memory_dir,
            retrieval=RetrievalWeights(
                relevance=0.4,    # sémantická relevance
                importance=0.4,   # důležitost
                recency=0.2       # časovost
            ),
            lifecycle=LifecycleConfig(
                decay_rate=0.02,           # pomalý decay
                decay_threshold=0.1,       # nízky práh pro uchování
                merge_similarity_threshold=0.85,
                abstraction_cluster_size=3,
                auto_maintenance_interval=20,  # častější údržba
            ),
            use_llm_importance_scoring=False,  # zatím bez LLM scoring
            recency_half_life_days=14.0,       # delší paměť
        )

        self.system = MemorySystem(provider=LocalProvider(), config=mem_config)
        logger.info(f"Neural memory inicializován v: {self.memory_dir}")

    def store(self, content: str, importance: float = 0.5, context: str = None,
              tags: List[str] = None, metadata: dict = None) -> Optional[str]:
        """Uloží informaci do paměti"""
        if not self.system:
            return None

        try:
            memory = self.system.store(
                content=content,
                importance=importance,
                context=context,
                tags=tags or [],
                metadata=metadata or {}
            )
            logger.info(f"Uloženo do paměti: {content[:50]}...")
            return memory.id
        except Exception as e:
            logger.error(f"Chyba při ukládání do paměti: {e}")
            return None

    def recall(self, query: str, top_k: int = 5, min_importance: float = 0.0) -> List[dict]:
        """Vyhledá relevantní vzpomínky"""
        if not self.system:
            return []

        try:
            results = self.system.recall(
                query=query,
                top_k=top_k,
                min_importance=min_importance
            )

            memories = []
            for r in results:
                memories.append({
                    "content": r.memory.content,
                    "importance": r.memory.importance,
                    "score": r.final_score,
                    "tags": r.memory.tags,
                    "metadata": r.memory.metadata,
                    "created_at": r.memory.created_at.isoformat() if r.memory.created_at else None
                })

            logger.info(f"Nalezeno {len(memories)} vzpomínek pro: {query}")
            return memories
        except Exception as e:
            logger.error(f"Chyba při vyhledávání v paměti: {e}")
            return []

    def get(self, memory_id: str) -> Optional[dict]:
        """Získá konkrétní vzpomínku"""
        if not self.system:
            return None

        try:
            memory = self.system.get(memory_id)
            if memory:
                return {
                    "content": memory.content,
                    "importance": memory.importance,
                    "tags": memory.tags,
                    "metadata": memory.metadata,
                    "created_at": memory.created_at.isoformat() if memory.created_at else None
                }
        except Exception as e:
            logger.error(f"Chyba při získávání vzpomínky {memory_id}: {e}")
        return None

    def forget(self, memory_id: str) -> bool:
        """Zapomene vzpomínku"""
        if not self.system:
            return False

        try:
            self.system.forget(memory_id)
            logger.info(f"Zapomenuto: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Chyba při zapomínání {memory_id}: {e}")
            return False

    def run_maintenance(self) -> dict:
        """Spustí údržbu paměti"""
        if not self.system:
            return {"error": "Neural memory není dostupná"}

        try:
            return self.system.run_maintenance()
        except Exception as e:
            logger.error(f"Chyba při údržbě paměti: {e}")
            return {"error": str(e)}

    def stats(self) -> dict:
        """Statistiky paměti"""
        if not self.system:
            return {"error": "Neural memory není dostupná"}

        try:
            s = self.system.stats()
            return {
                "total_memories": s.total_memories,
                "avg_importance": s.avg_importance,
                "by_category": dict(s.by_category) if s.by_category else {}
            }
        except Exception as e:
            logger.error(f"Chyba při získávání statistik: {e}")
            return {"error": str(e)}

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