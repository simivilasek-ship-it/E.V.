"""
JARVIS v3.0 — Neural Memory System
Integrovaný brain-inspired memory layer pro JARVIS
"""

import os
import logging
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
        """Získá kontext z paměti pro aktuální dotaz"""
        memories = self.recall(current_query, top_k=top_k, min_importance=0.2)

        if not memories:
            return ""

        context_parts = []
        for mem in memories:
            if mem["tags"] and "conversation" in mem["tags"]:
                context_parts.append(f"Previous: {mem['content']}")
            else:
                context_parts.append(f"Memory: {mem['content']}")

        context = "\n".join(context_parts)
        logger.info(f"Kontext z paměti: {len(context)} znaků")
        return context