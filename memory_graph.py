"""
memory_graph.py

Lightweight SQLite-backed graph store for JARVIS (MVP).
Stores entities and relations (triplets) with timestamps, source and confidence.
Provides simple embedding stub + fuzzy name resolution.
"""
from __future__ import annotations
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import List, Optional, Dict, Tuple

try:
    from memory import get_embedding_engine
    _HAS_EMB = True
except Exception:
    _HAS_EMB = False


_GRAPH_SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  embedding TEXT,
  metadata TEXT
);

CREATE TABLE IF NOT EXISTS relations (
  id INTEGER PRIMARY KEY,
  subject_id INTEGER NOT NULL,
  predicate TEXT NOT NULL,
  object_id INTEGER NOT NULL,
  ts REAL NOT NULL,
  source TEXT,
  confidence REAL DEFAULT 1.0,
  FOREIGN KEY(subject_id) REFERENCES entities(id),
  FOREIGN KEY(object_id) REFERENCES entities(id)
);

CREATE INDEX IF NOT EXISTS idx_rel_subject_pred ON relations(subject_id, predicate);
CREATE INDEX IF NOT EXISTS idx_rel_object ON relations(object_id);
"""


class SQLiteGraphStore:
    def __init__(self, db_path: Path):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._conn:
            self._conn.executescript(_GRAPH_SCHEMA)

    # low-level helpers
    def _execute(self, sql: str, params=()):
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def add_entity(self, name: str, embedding: Optional[List[float]] = None, metadata: Optional[dict] = None) -> int:
        """Insert or return existing entity id by exact name match (case-insensitive).
        Embedding is stored as JSON text.
        Returns entity id."""
        name = name.strip()
        if not name:
            raise ValueError("empty name")
        with self._lock:
            cur = self._conn.execute("SELECT id FROM entities WHERE LOWER(name)=LOWER(?)", (name,))
            row = cur.fetchone()
            if row:
                return int(row["id"])
            emb_json = json.dumps(embedding) if embedding is not None else None
            meta_json = json.dumps(metadata or {})
            cur = self._conn.execute(
                "INSERT INTO entities(name, embedding, metadata) VALUES (?,?,?)",
                (name, emb_json, meta_json)
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def find_entities_by_name(self, name: str, top_k: int = 6) -> List[Dict]:
        """Fuzzy lookup by name using embedding similarity (if available) or substring match."""
        name = name.strip()
        if not name:
            return []
        results: List[Tuple[int, float, str]] = []
        with self._lock:
            rows = list(self._conn.execute("SELECT id, name, embedding FROM entities").fetchall())
        # If embedding engine available, compute vector similarity; otherwise substring / overlap
        if _HAS_EMB:
            try:
                engine = get_embedding_engine()
                qv = engine.encode(name)
                import math
                def cos(a, b):
                    if not a or not b:
                        return 0.0
                    da = sum(x*x for x in a) ** 0.5
                    db = sum(x*x for x in b) ** 0.5
                    if da == 0 or db == 0:
                        return 0.0
                    return sum(x*y for x,y in zip(a,b)) / (da*db)
                for r in rows:
                    eid = r["id"]
                    ename = r["name"]
                    emb_json = r["embedding"]
                    score = 0.0
                    if emb_json:
                        try:
                            vec = json.loads(emb_json)
                            score = cos(qv, vec)
                        except Exception:
                            score = 0.0
                    # fallback: name substring
                    if score <= 0 and name.lower() in ename.lower():
                        score = 0.3
                    results.append((eid, score, ename))
                results.sort(key=lambda x: x[1], reverse=True)
                return [{'id': r[0], 'score': r[1], 'name': r[2]} for r in results[:top_k]]
            except Exception:
                pass
        # fallback substring/overlap
        lname = name.lower()
        for r in rows:
            eid = r["id"]
            ename = r["name"]
            score = 1.0 if lname == ename.lower() else (0.6 if lname in ename.lower() or ename.lower() in lname else 0.0)
            if score > 0:
                results.append((eid, score, ename))
        results.sort(key=lambda x: x[1], reverse=True)
        return [{'id': r[0], 'score': r[1], 'name': r[2]} for r in results[:top_k]]

    def add_relation(self, subject_name: str, predicate: str, object_name: str,
                     ts: Optional[float] = None, source: Optional[str] = None, confidence: float = 1.0) -> int:
        ts = ts or time.time()
        s_id = self.add_entity(subject_name)
        o_id = self.add_entity(object_name)
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO relations(subject_id, predicate, object_id, ts, source, confidence) VALUES (?,?,?,?,?,?)",
                (s_id, predicate, o_id, ts, source, float(confidence))
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def query_relations_for_text(self, text: str, hops: int = 1, max_results: int = 20) -> List[dict]:
        """Find entities mentioned in text and return 1-hop relations as evidence lines.
        Returns list of dicts with subject, predicate, object, ts, source, confidence.
        """
        if not text:
            return []
        found = []
        # simple name matching: check every entity if its name is substring of text
        with self._lock:
            rows = list(self._conn.execute("SELECT id, name FROM entities").fetchall())
        matches = [r for r in rows if str(r['name']).lower() in text.lower()]
        matched_ids = [int(r['id']) for r in matches]
        with self._lock:
            rels = []
            for mid in matched_ids:
                q = self._conn.execute(
                    "SELECT r.*, es.name as subject_name, eo.name as object_name FROM relations r "
                    "JOIN entities es ON r.subject_id=es.id JOIN entities eo ON r.object_id=eo.id "
                    "WHERE r.subject_id=? OR r.object_id=? ORDER BY r.ts DESC LIMIT ?",
                    (mid, mid, max_results)
                ).fetchall()
                for rr in q:
                    rels.append({
                        'subject': rr['subject_name'],
                        'predicate': rr['predicate'],
                        'object': rr['object_name'],
                        'ts': rr['ts'], 'source': rr['source'], 'confidence': rr['confidence']
                    })
        return rels[:max_results]

    def dump_graph(self, limit_nodes: int = 80, limit_links: int = 120) -> dict:
        with self._lock:
            nodes = list(self._conn.execute("SELECT id, name FROM entities ORDER BY id DESC LIMIT ?", (limit_nodes,)).fetchall())
            links = list(self._conn.execute(
                "SELECT r.subject_id as s, r.object_id as o, r.predicate as p FROM relations r ORDER BY r.ts DESC LIMIT ?",
                (limit_links,)).fetchall())
        nds = [{'id': str(n['id']), 'label': n['name'], 'group': 'entity', 'importance': 0.5} for n in nodes]
        lks = [{'source': str(l['s']), 'target': str(l['o']), 'label': l['p']} for l in links]
        return {'nodes': nds, 'links': lks}


# Thin compatibility wrapper
class GraphStore:
    def __init__(self, db_path: Path):
        self._store = SQLiteGraphStore(db_path)

    def add_relation(self, subject: str, predicate: str, obj: str, ts: Optional[float] = None, source: Optional[str] = None, confidence: float = 1.0):
        return self._store.add_relation(subject, predicate, obj, ts=ts, source=source, confidence=confidence)

    def find_entities(self, name: str, top_k: int = 6):
        return self._store.find_entities_by_name(name, top_k=top_k)

    def query_relations_for_text(self, text: str, hops: int = 1):
        return self._store.query_relations_for_text(text, hops=hops)

    def dump(self):
        return self._store.dump_graph()
