"""
JARVIS v4.4 — Neural Memory System + Daily Summarizer
Integrovaný brain-inspired memory layer pro JARVIS.
DailySummarizer extrahuje fakta z dnešních konverzací a ukládá do UserProfile.
"""

from __future__ import annotations
import os
import json
import logging
import threading
import time
from datetime import date
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
#  EMBEDDING ENGINE (opt-in — sentence-transformers)
# ══════════════════════════════════════════════════════

class EmbeddingEngine:
    """Lokální embeddingy přes sentence-transformers. Fallback: TF-IDF keyword overlap."""

    MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    def __init__(self):
        self._model = None
        self._available = False
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.MODEL)
            self._available = True
            logger.info("EmbeddingEngine: sentence-transformers OK")
        except ImportError:
            logger.warning(
                "EmbeddingEngine: sentence-transformers není nainstalováno — "
                "paměť používá keyword fallback (horší recall). "
                "Pro sémantické vyhledávání: pip install sentence-transformers"
            )

    def encode(self, text: str) -> list:
        if self._available and self._model:
            return self._model.encode(text).tolist()
        return []  # prázdné = fallback na keyword search

    def similarity(self, a: str, b: str) -> float:
        """Kosinová podobnost. Pokud embeddingy nejsou, vrátí keyword overlap score."""
        if self._available and self._model:
            import numpy as np
            va = self._model.encode(a)
            vb = self._model.encode(b)
            return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-9))
        # Fallback: keyword overlap
        sa, sb = set(a.lower().split()), set(b.lower().split())
        return len(sa & sb) / (len(sa | sb) + 1e-9)

    @property
    def available(self) -> bool:
        return self._available


_embedding_engine: "EmbeddingEngine | None" = None


def get_embedding_engine() -> EmbeddingEngine:
    global _embedding_engine
    if _embedding_engine is None:
        _embedding_engine = EmbeddingEngine()
    return _embedding_engine


# ══════════════════════════════════════════════════════
#  VESTAVĚNÁ JSON PAMĚŤ (fallback — bez závislostí)
# ══════════════════════════════════════════════════════

import sqlite3
import uuid
import math as _math


class _SQLiteMemoryStore:
    """
    Persistentní paměť v SQLite.
    Drop-in náhrada za původní JSON store — stejné API.
    SQLite je výrazně rychlejší pro velké paměti a nepotřebuje
    načítat vše do RAM při každém spuštění.
    """

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS memories (
        id           TEXT PRIMARY KEY,
        content      TEXT NOT NULL,
        importance   REAL NOT NULL DEFAULT 0.5,
        tags         TEXT NOT NULL DEFAULT '[]',
        metadata     TEXT NOT NULL DEFAULT '{}',
        created_at   REAL NOT NULL,
        last_access  REAL NOT NULL,
        access_count INTEGER NOT NULL DEFAULT 0,
        priority     INTEGER NOT NULL DEFAULT 0,
        ttl_seconds  INTEGER NOT NULL DEFAULT 0,
        expires_at   REAL NOT NULL DEFAULT 0,
        access_score REAL NOT NULL DEFAULT 0.0
    );
    CREATE INDEX IF NOT EXISTS idx_importance   ON memories(importance);
    CREATE INDEX IF NOT EXISTS idx_created_at  ON memories(created_at);
    CREATE INDEX IF NOT EXISTS idx_expires_at  ON memories(expires_at);
    CREATE INDEX IF NOT EXISTS idx_priority    ON memories(priority);
    CREATE INDEX IF NOT EXISTS idx_last_access ON memories(last_access);
    CREATE INDEX IF NOT EXISTS idx_access_score ON memories(access_score);
    """

    def __init__(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        self._db_path = path / "memories.db"
        self._lock = threading.Lock()
        self._migrate_json(path)
        with self._connect() as con:
            # Nejdřív přidej nové sloupce do existující DB (idempotentní)
            self._add_columns(con)
            # Pak spusť schema (vytvoří tabulku pokud neexistuje)
            con.executescript(self._SCHEMA)

    @staticmethod
    def _add_columns(con) -> None:
        """Přidá TTL/priority/access_score sloupce do existující DB (idempotentní)."""
        for col, typedef in [
            ("priority",     "INTEGER NOT NULL DEFAULT 0"),
            ("ttl_seconds",  "INTEGER NOT NULL DEFAULT 0"),
            ("expires_at",   "REAL    NOT NULL DEFAULT 0"),
            ("access_score", "REAL    NOT NULL DEFAULT 0.0"),
        ]:
            try:
                con.execute(f"ALTER TABLE memories ADD COLUMN {col} {typedef}")
            except Exception:
                pass  # sloupec již existuje
        con.commit()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self._db_path, check_same_thread=False)
        con.row_factory = sqlite3.Row
        return con

    def _migrate_json(self, path: Path) -> None:
        """Přenese data ze starého memories.json do SQLite (jednorázově)."""
        json_file = path / "memories.json"
        if not json_file.exists():
            return
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            if not data:
                json_file.rename(path / "memories.json.migrated")
                return
            with self._connect() as con:
                con.executescript(self._SCHEMA)
                for e in data:
                    con.execute(
                        "INSERT OR IGNORE INTO memories"
                        "(id,content,importance,tags,metadata,created_at,last_access,access_count)"
                        " VALUES (?,?,?,?,?,?,?,?)",
                        (e["id"], e["content"], e["importance"],
                         json.dumps(e.get("tags", []), ensure_ascii=False),
                         json.dumps(e.get("metadata", {}), ensure_ascii=False),
                         e["created_at"], e["last_access"], e["access_count"]),
                    )
            json_file.rename(path / "memories.json.migrated")
            logger.info(f"Migrováno {len(data)} vzpomínek z JSON do SQLite")
        except Exception as e:
            logger.warning(f"JSON→SQLite migrace selhala: {e}")

    def store(self, content: str, importance: float, tags: List[str],
              metadata: dict, ttl_seconds: int = 0, priority: int = 0) -> str:
        mid = str(uuid.uuid4())[:8]
        now = time.time()
        expires_at = now + ttl_seconds if ttl_seconds > 0 else 0
        with self._lock, self._connect() as con:
            con.execute(
                "INSERT INTO memories VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (mid, content, importance,
                 json.dumps(tags, ensure_ascii=False),
                 json.dumps(metadata, ensure_ascii=False),
                 now, now, 0, priority, ttl_seconds, expires_at, 0.0),
            )
        return mid

    def recall(self, query: str, top_k: int, min_importance: float) -> List[dict]:
        q_words = set(query.lower().split())
        now = time.time()
        engine = get_embedding_engine()
        with self._lock, self._connect() as con:
            rows = con.execute(
                "SELECT * FROM memories WHERE importance >= ?"
                " AND (expires_at = 0 OR expires_at > ?)"
                " ORDER BY priority DESC, importance DESC",
                (min_importance, now),
            ).fetchall()

        results = []
        for row in rows:
            age_days = (now - row["created_at"]) / 86400
            recency  = _math.exp(-age_days / 14)
            importance = max(0.0, min(1.0, float(row["importance"])))
            recency    = max(0.0, min(1.0, recency))
            access_score = max(0.0, min(1.0, float(row["access_score"] or 0.0)))
            priority = max(0, int(row["priority"] or 0))
            if engine.available:
                sem_score = engine.similarity(query, row["content"])
                # Odmítni NaN / inf / záporné hodnoty z embedding modelu
                if not _math.isfinite(sem_score) or sem_score <= 0.0:
                    continue
                sem_score = min(1.0, sem_score)
                score = (
                    0.40 * sem_score +
                    0.25 * importance +
                    0.15 * recency +
                    0.15 * access_score +
                    0.05 * min(priority / 10.0, 1.0)
                )
            else:
                c_words = set(row["content"].lower().split())
                overlap = len(q_words & c_words)
                if overlap == 0:
                    continue
                sem_score = overlap / max(len(q_words), 1)
                score = (
                    0.40 * sem_score +
                    0.25 * importance +
                    0.15 * recency +
                    0.15 * access_score +
                    0.05 * min(priority / 10.0, 1.0)
                )
            results.append({
                "id": row["id"], "content": row["content"],
                "importance": row["importance"],
                "tags": json.loads(row["tags"]),
                "metadata": json.loads(row["metadata"]),
                "created_at": row["created_at"],
                "score": score,
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        top = results[:top_k]

        if top:
            ids = tuple(r["id"] for r in top)
            placeholders = ",".join("?" * len(ids))
            with self._lock, self._connect() as con:
                con.execute(
                    f"UPDATE memories SET last_access=?, access_count=access_count+1, "
                    f"access_score=MIN(access_score+0.25, 1.0) "
                    f"WHERE id IN ({placeholders})",
                    (now, *ids),
                )
        return top

    def forget(self, mid: str) -> bool:
        with self._lock, self._connect() as con:
            cur = con.execute("DELETE FROM memories WHERE id=?", (mid,))
        return cur.rowcount > 0

    def maintenance(self, decay_rate: float = 0.01,
                    min_importance: float = 0.05) -> dict:
        now = time.time()
        with self._lock, self._connect() as con:
            rows = con.execute("SELECT id, importance, created_at, access_score FROM memories").fetchall()
            for row in rows:
                # Long-term memories (access_score >= 5.0) nepodléhají decay
                if row["access_score"] >= 5.0:
                    continue
                age_days    = (now - row["created_at"]) / 86400
                new_imp     = row["importance"] * _math.exp(-decay_rate * age_days)
                if new_imp < min_importance:
                    con.execute("DELETE FROM memories WHERE id=?", (row["id"],))
                else:
                    con.execute("UPDATE memories SET importance=? WHERE id=?",
                                (new_imp, row["id"]))
            remaining = con.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        removed = len(rows) - remaining
        logger.info(f"Memory maintenance: odstraněno {removed} vzpomínek")
        return {"removed": removed, "remaining": remaining}

    def stats(self) -> dict:
        with self._lock, self._connect() as con:
            row = con.execute(
                "SELECT COUNT(*) as total, AVG(importance) as avg_imp FROM memories"
                " WHERE (expires_at = 0 OR expires_at > ?)", (time.time(),)
            ).fetchone()
        return {
            "total_memories": row["total"] or 0,
            "avg_importance": round(row["avg_imp"] or 0.0, 3),
        }

    def run_maintenance(self) -> dict:
        """Smaže expirované záznamy. Vrátí statistiku."""
        now = time.time()
        with self._lock, self._connect() as con:
            total_before = con.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            deleted = con.execute(
                "DELETE FROM memories WHERE expires_at > 0 AND expires_at < ?", (now,)
            ).rowcount
            con.commit()
            total_after = total_before - deleted
        if deleted:
            logger.info(f"Memory maintenance: smazáno {deleted} expirovaných záznamů")
        return {"deleted_expired": deleted, "total": total_after}


    def get_long_term(self, top_k: int = 20) -> list:
        """Vrátí vzpomínky s nejvyšším access_score — ty jsou 'permanentní'."""
        with self._lock, self._connect() as con:
            rows = con.execute(
                "SELECT * FROM memories WHERE access_score >= 2.0 "
                "ORDER BY access_score DESC LIMIT ?", (top_k,)
            ).fetchall()
        return [dict(r) for r in rows]

    def promote_to_long_term(self, memory_id: str) -> None:
        """Explicitně povýší vzpomínku na long-term (score = 10.0)."""
        with self._lock, self._connect() as con:
            con.execute("UPDATE memories SET access_score = 10.0 WHERE id = ?", (memory_id,))
            con.commit()


# Alias pro zpětnou kompatibilitu
_JSONMemoryStore = _SQLiteMemoryStore


def _similarity_score(a: str, b: str) -> float:
    """Jednoduchá word-overlap podobnost 0–1. Bez závislostí."""
    wa = set(a.lower().split())
    wb = set(b.lower().split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


try:
    import networkx as nx
except ImportError:
    nx = None


# ══════════════════════════════════════════════════════
#  THREE-TIER HIERARCHICAL MEMORY LAYER (v4.7)
# ══════════════════════════════════════════════════════

class EpisodicMemory:
    """
    Epizodická paměť (Krátkodobá):
    Udržuje kontext aktuální konverzace a dění na obrazovce za posledních 5 minut (300 sekund).
    Automaticky čistí staré záznamy.
    """
    def __init__(self, ttl_seconds: float = 300.0):
        self.ttl_seconds = ttl_seconds
        self.events: List[dict] = []
        self._lock = threading.Lock()

    def add_event(self, content: str, type_: str = "conversation", metadata: dict = None) -> None:
        """Přidá novou epizodickou událost s časovým razítkem."""
        with self._lock:
            self.events.append({
                "timestamp": time.time(),
                "content": content,
                "type": type_,
                "metadata": metadata or {}
            })
            self._prune()

    def _prune(self) -> None:
        """Odstraní události starší než 5 minut."""
        now = time.time()
        self.events = [e for e in self.events if now - e["timestamp"] <= self.ttl_seconds]

    def get_context(self) -> str:
        """Vrátí naformátovaný kontext za posledních 5 minut."""
        self._prune()
        if not self.events:
            return "Žádné nedávné události za posledních 5 minut."
        
        parts = []
        for e in self.events:
            dt = time.strftime("%H:%M:%S", time.localtime(e["timestamp"]))
            t_type = e["type"].upper()
            parts.append(f"[{dt}] ({t_type}): {e['content']}")
        return "\n".join(parts)


class ProceduralMemory:
    """
    Procedurální paměť (Dlouhodobá):
    Grafová databáze využívající networkx (s fallbackem na prostý slovník).
    Uchovává entity a vztahy (např. projekt X -> uses -> Python 3.11).
    Perzistuje do JSON souboru.
    """
    def __init__(self, persist_path: Path):
        self.persist_path = persist_path
        self._lock = threading.Lock()
        if nx is not None:
            self.graph = nx.DiGraph()
        else:
            self.graph = None
            self._nodes = {}  # fallback node storage
            self._edges = []  # fallback edge storage
        self._load()

    def _load(self):
        with self._lock:
            if not self.persist_path.exists():
                return
            try:
                if self.graph is not None:
                    with open(self.persist_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self.graph = nx.node_link_graph(data)
                    logger.info(f"Procedurální paměť načtena: {self.graph.number_of_nodes()} uzlů, {self.graph.number_of_edges()} hran")
                else:
                    with open(self.persist_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._nodes = {n["id"]: n for n in data.get("nodes", [])}
                    self._edges = data.get("edges", [])
                    logger.info(f"Procedurální paměť (fallback) načtena: {len(self._nodes)} uzlů, {len(self._edges)} hran")
            except Exception as e:
                logger.warning(f"Chyba při načítání procedurální paměti: {e}")

    def _save(self):
        try:
            if self.graph is not None:
                data = nx.node_link_data(self.graph)
            else:
                data = {
                    "directed": True,
                    "multigraph": False,
                    "graph": {},
                    "nodes": [{"id": nid} for nid in self._nodes.keys()],
                    "edges": self._edges
                }
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Chyba při ukládání procedurální paměti: {e}")

    def add_relation(self, source: str, relation: str, target: str, metadata: dict = None) -> None:
        """Přidá hranu (vztah) mezi dva uzly."""
        with self._lock:
            source = source.strip()
            target = target.strip()
            relation = relation.strip()
            if not source or not target or not relation:
                return
            
            if self.graph is not None:
                self.graph.add_node(source, type="entity")
                self.graph.add_node(target, type="entity")
                self.graph.add_edge(source, target, relation=relation, metadata=metadata or {})
            else:
                self._nodes[source] = {"id": source}
                self._nodes[target] = {"id": target}
                # Check for existing
                exists = False
                for edge in self._edges:
                    if edge["source"] == source and edge["target"] == target:
                        edge["relation"] = relation
                        edge["metadata"] = metadata or {}
                        exists = True
                        break
                if not exists:
                    self._edges.append({
                        "source": source,
                        "target": target,
                        "relation": relation,
                        "metadata": metadata or {}
                    })
            self._save()
            logger.info(f"Přidán vztah: [{source}] --({relation})--> [{target}]")

    def remove_relation(self, source: str, target: str) -> bool:
        """Odstraní hranu mezi uzly."""
        with self._lock:
            if self.graph is not None:
                if self.graph.has_edge(source, target):
                    self.graph.remove_edge(source, target)
                    self._save()
                    return True
                return False
            else:
                initial_len = len(self._edges)
                self._edges = [e for e in self._edges if not (e["source"] == source and e["target"] == target)]
                if len(self._edges) < initial_len:
                    self._save()
                    return True
                return False

    def query_relations(self, query_text: str) -> str:
        """
        Vyhledá v textu dotazu známé entity (uzly) a vrátí jejich vztahy.
        Tím se LLM prompt obohatí o přesné okolní vztahy z grafu.
        """
        with self._lock:
            query_lower = query_text.lower()
            matching_nodes = []
            
            # Najdi uzly, které se vyskytují v dotazu
            nodes = list(self.graph.nodes) if self.graph is not None else list(self._nodes.keys())
            for node in nodes:
                if str(node).lower() in query_lower:
                    matching_nodes.append(node)
            
            if not matching_nodes:
                return ""
            
            relations_text = []
            # Pro každý odpovídající uzel najdi jeho přímé vztahy (odchozí i příchozí)
            for node in matching_nodes:
                if self.graph is not None:
                    # Odchozí vztahy
                    for successor in self.graph.successors(node):
                        edge_data = self.graph.get_edge_data(node, successor)
                        relation = edge_data.get("relation", "souvisí s")
                        relations_text.append(f"- '{node}' {relation} '{successor}'")
                    # Příchozí vztahy
                    for predecessor in self.graph.predecessors(node):
                        edge_data = self.graph.get_edge_data(predecessor, node)
                        relation = edge_data.get("relation", "souvisí s")
                        relations_text.append(f"- '{predecessor}' {relation} '{node}'")
                else:
                    for edge in self._edges:
                        if edge["source"] == node:
                            relations_text.append(f"- '{node}' {edge['relation']} '{edge['target']}'")
                        elif edge["target"] == node:
                            relations_text.append(f"- '{edge['source']}' {edge['relation']} '{node}'")
            
            # Odstraň duplicity a seřaď
            unique_relations = sorted(list(set(relations_text)))
            if unique_relations:
                return "\n".join(unique_relations)
            return ""


# ══════════════════════════════════════════════════════
#  JARVIS MEMORY (unifikovaná fasáda)
# ══════════════════════════════════════════════════════

def _extract_entities_simple(text: str) -> list[tuple[str, str, str]]:
    """Very small heuristic extractor for graph relations.

    Returns list of (subject, predicate, object) triplets.
    """
    import re

    t = (text or "").strip()
    if not t:
        return []

    triplets: list[tuple[str, str, str]] = []

    # Examples:
    # "Můj brácha Jirka začal programovat v Rustu"
    m = re.search(r"\b(m[uů]j\s+br[áa]cha|bratr)\s+([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][\wÁČĎÉĚÍŇÓŘŠŤÚŮÝŽáčďéěíňóřšťúůýž-]{1,30})\b", t)
    if m:
        person = m.group(2)
        triplets.append(("Ty", "MÁ_BRATRA", person))

    # "Jirka se učí Rust" / "Jirka programuje v Rustu"
    m2 = re.search(r"\b([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][\wÁČĎÉĚÍŇÓŘŠŤÚŮÝŽáčďéěíňóřšťúůýž-]{1,30})\s+(se\s+u[cč]i|u[cč]i\s+se|programuje\s+v|k[oó]duje\s+v)\s+([A-Za-z][A-Za-z0-9_\-\+\.#]{1,40})\b", t)
    if m2:
        who = m2.group(1)
        what = m2.group(3)
        pred = "UČÍ_SE" if "u" in m2.group(2) else "PROGRAMUJE_V"
        triplets.append((who, pred, what))

    # "Mám rád X" / "Preferuji X"
    m3 = re.search(r"\b(m[aá]m\s+r[aá]d|preferuji|m[ou]j\s+obl[ií]ben[yý])\s+(.{2,40})$", t, re.I)
    if m3:
        obj = m3.group(2).strip(" .!?")
        if 2 <= len(obj) <= 40:
            triplets.append(("Ty", "MÁ_RÁD", obj))

    return triplets


class JarvisMemory:
    """
    Paměťová fasáda pro JARVIS.
    Preferuje neural-ai-memory pokud je nainstalovaná,
    jinak používá vestavěný JSON store (vždy funkční).
    """

    def __init__(self, config: dict):
        self.config = config
        mem_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "memory_data"
        mem_dir.mkdir(parents=True, exist_ok=True)

        # Inicializace Epizodické a Procedurální paměti
        self.episodic = EpisodicMemory()
        self.procedural = ProceduralMemory(mem_dir / "procedural_memory.json")

        # Initialize lightweight GraphStore (SQLite) for extracted triplets / facts
        try:
            from memory_graph import GraphStore
            self.graph_store = GraphStore(mem_dir / "memory_graph.db")
            logger.info(f"GraphStore inicializován v: {mem_dir / 'memory_graph.db'}")
        except Exception as e:
            logger.warning(f"Nelze inicializovat GraphStore: {e}")
            self.graph_store = None

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
        self._store = _SQLiteMemoryStore(mem_dir)
        logger.info(f"SQLite memory inicializován v: {mem_dir}")

        # Background auto-pruning přes scheduler (každou hodinu, ne blokující)
        self._schedule_background_pruning()

    def _schedule_background_pruning(self) -> None:
        """Registruje hodinový background pruning do Scheduleru.
        Nikdy neblokuje uživatelský dotaz — běží jako samostatná úloha.
        """
        try:
            from scheduler import get_scheduler
            scheduler = get_scheduler()

            def _prune_task():
                try:
                    result = self.run_maintenance()
                    logger.info(f"Background memory pruning: {result}")
                except Exception as e:
                    logger.warning(f"Background pruning selhal: {e}")

            # Jednou za hodinu (3600 s), poprvé za 5 minut po startu
            scheduler._add(
                fn=_prune_task,
                args=(), kwargs={},
                fire_at=time.time() + 300,
                repeat=3600.0,
                name="memory_auto_prune",
            )
            logger.info("Memory background pruning naplánován (každou hodinu)")
        except Exception as e:
            logger.debug(f"Memory pruning scheduling selhal (nevadí): {e}")

    # ── Conflict resolution ────────────────────────────

    # Vzory naznačující fakta, která se mohou měnit (jméno, preferovaný jazyk…)
    _CONFLICT_PATTERNS = [
        (r"\bjmenuji\s+se\b|\bjmeno\s+je\b|\bjsem\s+\w+\b", "jméno"),
        (r"\bpracuji\s+(s|v|na)\b|\bprogramuji\s+v\b|\bpouzivaml?\b", "technologie"),
        (r"\bbydlim\s+v\b|\bmestu\b|\badresa\b",              "lokalita"),
        (r"\bpracuji\s+pro\b|\bzamestnani\b|\bfirma\b",       "zaměstnání"),
    ]

    def _extract_graph_relations(self, content: str) -> None:
        """Best-effort extraction of simple relations into procedural memory and SQLite graph store."""
        try:
            triplets = _extract_entities_simple(content)
            for s, p, o in triplets:
                meta = {"source": "heuristic", "ts": time.time()}
                try:
                    self.procedural.add_relation(s, p, o, metadata=meta)
                except Exception:
                    pass
                # also store into lightweight GraphStore if available
                try:
                    if getattr(self, 'graph_store', None):
                        self.graph_store.add_relation(s, p, o, ts=meta['ts'], source=meta['source'], confidence=0.9)
                        # Optionally run auto-merge (conservative, opt-in via config)
                        try:
                            from config import CONFIG
                            if CONFIG.get('memory_graph_auto_merge', False):
                                thr = float(CONFIG.get('memory_graph_merge_threshold', 0.88))
                                merged = self.graph_store.auto_merge_by_embedding(thr)
                                if merged:
                                    logger.info(f"MemoryGraph: auto-merged {len(merged)} pairs")
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

    def check_conflict(self, new_content: str, top_k: int = 5) -> Optional[dict]:
        """Zjistí, zda nový záznam odporuje existujícím vzpomínkám.

        Vrátí {"old": str, "new": str, "topic": str} nebo None.
        Algoritmus: pro každý vzor kategorie zkontroluj, zda staré vzpomínky
        obsahují stejné klíčové slovo ale jiný kontext.
        """
        import re
        for pattern, topic in self._CONFLICT_PATTERNS:
            if not re.search(pattern, new_content, re.I):
                continue
            existing = self.recall(topic, top_k=top_k, min_importance=0.1)
            for mem in existing:
                old = mem.get("content", "")
                if not old or old == new_content:
                    continue
                # Jednoduchá heuristika: oba záznamy matchují stejný vzor
                if re.search(pattern, old, re.I):
                    # Pokud jsou různé → konflikt
                    if _similarity_score(old, new_content) < 0.85:
                        return {"old": old, "new": new_content, "topic": topic}
        return None

    def store_with_conflict_check(
        self,
        content: str,
        importance: float = 0.5,
        on_conflict=None,
        **kwargs,
    ) -> Optional[str]:
        """Uloží vzpomínku, ale nejdříve zkontroluje konflikty.

        on_conflict(old, new, topic) → pokud vrátí False, uložení se přeskočí.
        Pokud on_conflict není zadán, stará vzpomínka se označí jako neaktivní
        (importance → 0.05) a nová se uloží.
        """
        conflict = self.check_conflict(content)
        if conflict:
            if on_conflict:
                should_store = on_conflict(conflict["old"], conflict["new"], conflict["topic"])
                if not should_store:
                    return None
            else:
                # Automaticky: degraduj starou vzpomínku
                logger.info(
                    f"Memory conflict [{conflict['topic']}]: "
                    f"'{conflict['old'][:60]}' → '{conflict['new'][:60]}'"
                )
                old_results = self.recall(conflict["old"][:40], top_k=3)
                for r in old_results:
                    mid = r.get("id") or r.get("memory_id")
                    if mid:
                        try:
                            self._store._conn().execute(
                                "UPDATE memories SET importance=0.05 WHERE id=?", (mid,))
                            self._store._conn().commit()
                        except Exception:
                            pass

        return self.store(content, importance=importance, **kwargs)

    # ── Store ──────────────────────────────────────────

    def store(self, content: str, importance: float = 0.5, context: str = None,
              tags: List[str] = None, metadata: dict = None,
              ttl_seconds: int = 0, priority: int = 0) -> Optional[str]:
        # Graph extraction (best-effort)
        try:
            if bool(self.config.get("graph_extraction_enabled", True)):
                self._extract_graph_relations(content)
        except Exception:
            pass

        if self.system:
            try:
                mem = self.system.store(content=content, importance=importance,
                                        context=context, tags=tags or [],
                                        metadata=metadata or {})
                return mem.id
            except Exception as e:
                logger.error(f"Neural memory store chyba: {e}")
                return None
        return self._store.store(content, importance, tags or [], metadata or {},
                                 ttl_seconds=ttl_seconds, priority=priority)

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
        parts = []
        for mem in memories or []:
            if mem.get("tags") and "conversation" in mem["tags"]:
                parts.append(f"Previous: {mem['content']}")
            else:
                parts.append(f"Memory: {mem['content']}")

        # Add knowledge-graph relations (GraphStore preferred, fallback to procedural)
        try:
            rels = []
            if getattr(self, 'graph_store', None):
                try:
                    rels = self.graph_store.query_relations_for_text(current_query)
                except Exception:
                    rels = []
            if rels:
                parts.append("\nKnown relations (graph):\n" + "\n".join(
                    f"- '{r['subject']}' {r['predicate']} '{r['object']}' (src:{r.get('source')}, conf:{r.get('confidence')})" for r in rels
                ))
            else:
                # fallback to procedural memory text
                rel = self.procedural.query_relations(current_query)
                if rel:
                    parts.append("\nKnown relations (graph):\n" + rel)
        except Exception:
            pass

        context = "\n".join(parts)
        if context:
            logger.info(f"Kontext z paměti: {len(context)} znaků")
        return context

    def compress_old_memories(self, days_old: int = 7, max_to_compress: int = 20) -> str:
        """Zkomprimuje staré vzpomínky do jedné souhrnné.

        Vzpomínky starší než days_old → sloučí je do jednoho textu přes LLM
        → uloží jako novou vzpomínku s vysokou důležitostí
        → smaže originály
        """
        if not self._store:
            return "Paměť není inicializována."

        cutoff = time.time() - (days_old * 86400)

        with self._store._lock, self._store._connect() as con:
            old_rows = con.execute(
                "SELECT id, content FROM memories "
                "WHERE created_at < ? AND access_score < 2.0 "
                "LIMIT ?", (cutoff, max_to_compress)
            ).fetchall()

        if len(old_rows) < 3:
            return f"Příliš málo starých vzpomínek ({len(old_rows)}) k sloučení."

        # Sestav text pro LLM
        combined = "\n".join(f"- {r['content'][:100]}" for r in old_rows)

        # Pokus o LLM komprimaci
        compressed = combined  # fallback bez LLM
        try:
            import requests
            from config import CONFIG
            r = requests.post(CONFIG.get("ollama_url", "http://localhost:11434/api/chat"),
                json={"model": CONFIG.get("ollama_model", "qwen2.5:3b"),
                      "messages": [{"role": "user", "content":
                          f"Zkomprimuj tyto záznamy do 2-3 klíčových faktů:\n{combined}"}],
                      "stream": False, "options": {"num_predict": 200}},
                timeout=15)
            if r.ok:
                compressed = r.json().get("message", {}).get("content", combined)
        except Exception:
            pass

        # Ulož komprimovanou verzi
        new_id = self.store(f"[KOMPRIMOVÁNO] {compressed}", importance=0.8,
                            tags=["compressed"], metadata={"source_count": len(old_rows)})

        # Smaž originály
        ids = [r["id"] for r in old_rows]
        with self._store._lock, self._store._connect() as con:
            con.execute(f"DELETE FROM memories WHERE id IN ({','.join('?'*len(ids))})", ids)
            con.commit()

        return f"Sloučeno {len(old_rows)} vzpomínek → nová ID: {new_id}"

    def export_memories(self, path: str) -> str:
        """Exportuje paměť do JSON souboru."""
        import json as _json
        from pathlib import Path as _Path
        if not self._store:
            return "Paměť není inicializována."
        memories = self.recall("", top_k=1000, min_importance=0.0)
        _Path(path).write_text(_json.dumps(memories, ensure_ascii=False, indent=2), encoding="utf-8")
        return f"Exportováno {len(memories)} vzpomínek do {path}"

    def import_memories(self, path: str) -> str:
        """Importuje paměť z JSON souboru."""
        import json as _json
        from pathlib import Path as _Path
        data = _json.loads(_Path(path).read_text(encoding="utf-8"))
        imported = 0
        for m in data:
            try:
                self.store(m.get("content", ""), importance=m.get("importance", 0.5),
                          tags=m.get("tags", []), metadata=m.get("metadata", {}))
                imported += 1
            except Exception:
                pass
        return f"Importováno {imported}/{len(data)} vzpomínek"


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

        # Memory pruning — kondenzuj staré konverzace před extrakcí faktů
        try:
            from memory import get_conversation_summarizer
            from user_profile import get_user_profile
            from config import CONFIG
            pruner = get_conversation_summarizer(CONFIG)
            result = pruner.prune_and_save(
                self.memory._store, get_user_profile(),
                CONFIG.get("ollama_url", "http://localhost:11434/api/chat"),
                CONFIG.get("ollama_model", "qwen2.5:3b")
            )
            logger.info(f"Memory pruning: {result}")
        except Exception as e:
            logger.warning(f"Memory pruning selhal: {e}")

        with self._lock:
            # Retry až 3× s exponential backoff (Ollama může být dočasně zahlcena)
            import time as _time
            for attempt in range(3):
                try:
                    result = self._do_summarize()
                    if result:
                        return result
                    return ""
                except Exception as e:
                    if attempt < 2:
                        wait = 2 ** attempt  # 1s, 2s
                        logger.warning(f"DailySummarizer pokus {attempt+1}/3 selhal: {e} — retry za {wait}s")
                        _time.sleep(wait)
                    else:
                        logger.error(f"DailySummarizer selhalo po 3 pokusech: {e}")
                        return ""
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


# ══════════════════════════════════════════════════════
#  CONVERSATION SUMMARIZER (context-aware memory pruning)
# ══════════════════════════════════════════════════════

class ConversationSummarizer:
    """Automaticky kondenzuje staré konverzační vlákna do faktů o uživateli.

    Logika:
    - Spustí se když je počet zpráv v historii > max_history
    - Vezme nejstarší blok zpráv (první third) a požádá LLM o sumarizaci
    - Výsledek uloží do user_profile jako kondenzovaná fakta
    - Staré zprávy smaže z paměti
    """

    def __init__(self, config: dict, max_history: int = 40):
        self.config = config
        self.max_history = max_history

    def should_prune(self, conversation_count: int) -> bool:
        """True pokud je čas na pruning."""
        return conversation_count >= self.max_history

    def summarize_and_prune(self, memories: list, ollama_url: str, model: str):
        """Vezme seznam vzpomínek, zkondenzuje staré, vrátí (pruned_list, summary).

        memories — seznam dict {"content": str, "created_at": float, ...}
        Vrátí (nový_kratší_seznam, textový_souhrn)
        """
        if len(memories) < self.max_history:
            return memories, ""

        # Vezmi první třetinu jako "staré"
        split = len(memories) // 3
        old_memories = memories[:split]
        recent_memories = memories[split:]

        # Sestav kontext pro sumarizaci
        context = "\n".join(m.get("content", "")[:200] for m in old_memories)

        prompt = f"""Toto jsou starší konverzace s uživatelem JARVIS asistenta.
Vytvoř stručný souhrn klíčových faktů o uživateli (max 5 vět):

{context}

Souhrn (jen fakta o uživateli, jeho preferencích a zvyklostech):"""

        summary = ""
        try:
            import requests
            r = requests.post(
                ollama_url,
                json={"model": model, "messages": [{"role": "user", "content": prompt}],
                      "stream": False, "options": {"temperature": 0.1, "num_predict": 300}},
                timeout=30,
            )
            if r.ok:
                summary = r.json().get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.warning(f"ConversationSummarizer LLM chyba: {e}")
            # Fallback: simple concatenation
            summary = f"Souhrn {len(old_memories)} starších konverzací: " + context[:500]

        return recent_memories, summary

    def prune_and_save(self, memory_store, user_profile, ollama_url: str, model: str) -> str:
        """Hlavní metoda — pruneuje paměť a ukládá souhrn do user_profile."""
        try:
            # Získej všechny konverzační vzpomínky
            memories = memory_store.recall("", top_k=200, min_importance=0.0)
            conv_memories = [m for m in memories if "conversation" in str(m.get("tags", []))]

            if not self.should_prune(len(conv_memories)):
                return f"Pruning nepotřebný ({len(conv_memories)} zpráv < {self.max_history})"

            pruned, summary = self.summarize_and_prune(conv_memories, ollama_url, model)

            if summary:
                # Ulož souhrn jako poznámku do user_profile
                # set() volá _save() interně, takže explicitní save() není potřeba
                user_profile.set("conversation_summary", summary, confidence=0.9)

            return f"Zkondenzováno {len(conv_memories) - len(pruned)} starých konverzací. Souhrn uložen do profilu."
        except Exception as e:
            return f"Pruning selhal: {e}"


_summarizer: "ConversationSummarizer | None" = None


def get_conversation_summarizer(config: dict = None) -> ConversationSummarizer:
    global _summarizer
    if _summarizer is None:
        from config import CONFIG
        _summarizer = ConversationSummarizer(config or CONFIG)
    return _summarizer