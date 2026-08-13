"""
E.V. — Graph Extractor (GraphRAG vrstva)
Automaticky extrahuje entity a vztahy z konverzací a ukládá do memory_graph.

Extrakce probíhá ve dvou módech:
  1. Regex/heuristika (rychlý, bez LLM) — jména, projekty, data, preference
  2. LLM extraction (pomalejší, přesnější) — přes cloud nebo Ollama

Výsledek: při každém dotazu E.V. dostane kontext jako:
  "Petr pracuje na projektu Alpha. Alpha má deadline 15.6. Ty preferuješ tmavé téma."
"""
from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Heuristická extrakce (bez LLM) ───────────────────────────────────────────

# Jména osob (velké písmeno, ne na začátku věty)
_NAME_PATTERN = re.compile(
    r"(?<![.!?]\s)(?<!\n)(?<!\A)\b([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]{2,})\b"
    r"(?:\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]{2,})?",
    re.UNICODE,
)

# Projekty a klíčová slova
_PROJECT_PATTERN = re.compile(
    r"\bprojekt[u]?\s+([A-Za-z0-9_\-]+)\b"
    r"|\b(Alpha|Beta|Gamma|MVP|v\d+\.\d+)\b",
    re.IGNORECASE,
)

# Preference uživatele
_PREFER_PATTERN = re.compile(
    r"(?:preferuji|mám rád|líbí se mi|chci|nerada|nechci|nenávidím)\s+(.{5,60}?)(?:[.,!?]|$)",
    re.IGNORECASE,
)

# Deadline / datum
_DATE_PATTERN = re.compile(
    r"\b(\d{1,2})[.\/-](\d{1,2})(?:[.\/-](\d{2,4}))?\b"
    r"|\b(zítra|pozítří|v\s+pondělí|v\s+úterý|v\s+středu|v\s+čtvrtek|v\s+pátek)\b",
    re.IGNORECASE,
)

# Pracovní vztahy: "X pracuje na Y", "X je vedoucí Y", "X patří do Y"
_WORK_PATTERN = re.compile(
    r"([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]{2,})\s+"
    r"(pracuje na|je vedoucí|patří do|spolupracuje s|vede|spravuje)\s+"
    r"([A-Za-záčďéěíňóřšťúůýž0-9_\-\s]{3,40}?)(?:[.,!?]|$)",
    re.UNICODE,
)

# Stoplist — nezajímavá slova která se chybně detekují jako jména
_STOPWORDS = {
    "Ahoj", "Dobry", "Dobré", "Prosim", "Prosím", "Nevim", "Nevím",
    "Umis", "Umíš", "Pokud", "Kdyz", "Když", "Takze", "Takže",
    "Napiš", "Napíš", "Otevři", "Spusť", "Zkus", "Můžeš", "Chceš",
    "Jarvis", "E.V.", "Yes", "Okay", "Thanks",
}


def heuristic_extract(text: str) -> List[Tuple[str, str, str]]:
    """
    Rychlá regex extrakce trojic (subject, predicate, object) z textu.
    Vrátí seznam trojic (subject, predicate, object).
    """
    triplets: List[Tuple[str, str, str]] = []

    # Pracovní vztahy
    for m in _WORK_PATTERN.finditer(text):
        subj = m.group(1).strip()
        pred = m.group(2).strip()
        obj  = m.group(3).strip().rstrip(".,!?")
        if subj not in _STOPWORDS and len(obj) > 2:
            triplets.append((subj, pred, obj))

    # Preference uživatele
    for m in _PREFER_PATTERN.finditer(text):
        pref = m.group(1).strip().rstrip(".,!?")
        if len(pref) > 3:
            triplets.append(("uživatel", "preferuje", pref))

    # Projekty zmíněné v textu
    for m in _PROJECT_PATTERN.finditer(text):
        proj = (m.group(1) or m.group(2) or "").strip()
        if proj and proj not in _STOPWORDS:
            triplets.append(("uživatel", "pracuje na projektu", proj))

    return triplets


def llm_extract(text: str, config: dict = None) -> List[Tuple[str, str, str]]:
    """
    LLM-based extrakce entit a vztahů (přesnější než regex).
    Zkusí cloud (Groq) nebo lokální Ollama.
    Vrátí seznam trojic (subject, predicate, object).
    """
    if config is None:
        try:
            from config import CONFIG
            config = CONFIG
        except Exception:
            config = {}

    prompt = (
        "Extrahuj entity a vztahy z tohoto textu pro znalostní graf. "
        "Vrať POUZE JSON pole trojic, žádný jiný text:\n"
        '[{"s": "entita1", "p": "vztah", "o": "entita2"}, ...]\n\n'
        f"Text:\n{text[:800]}"
    )
    messages = [{"role": "user", "content": prompt}]

    raw = ""
    # 1) Groq (nejrychlejší)
    try:
        from cloud_router import get_cloud_router
        cloud = get_cloud_router(config)
        if cloud.enabled:
            resp = cloud.call(messages, task_type="fast", temperature=0.0, max_tokens=400)
            raw = resp.content
    except Exception as e:
        logger.debug(f"LLM extrakce cloud selhal: {e}")

    # 2) Ollama fallback
    if not raw:
        try:
            import requests
            payload = {
                "model": config.get("ollama_model", "qwen2.5:3b"),
                "messages": messages,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.0, "num_predict": 400},
            }
            r = requests.post(config.get("ollama_url", "http://localhost:11434/api/chat"),
                              json=payload, timeout=30)
            r.raise_for_status()
            raw = r.json().get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.debug(f"LLM extrakce Ollama selhal: {e}")

    if not raw:
        return []

    # Parsuj JSON
    import json
    try:
        clean = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
        start = clean.find("[")
        end   = clean.rfind("]") + 1
        data  = json.loads(clean[start:end]) if start >= 0 else []
        result = []
        for item in data:
            s = str(item.get("s", "") or item.get("subject", "")).strip()
            p = str(item.get("p", "") or item.get("predicate", "")).strip()
            o = str(item.get("o", "") or item.get("object", "")).strip()
            if s and p and o and len(s) < 80 and len(o) < 80:
                result.append((s, p, o))
        return result
    except Exception as e:
        logger.debug(f"LLM extrakce JSON parse selhal: {e} | raw: {raw[:200]}")
        return []


# ── GraphRAG Memory Integration ───────────────────────────────────────────────

class GraphRAGMemory:
    """
    Rozšíření JarvisMemory o GraphRAG vrstvu.

    Při store_conversation() automaticky:
    - Extrahuje entity a vztahy (regex + optional LLM)
    - Uloží do SQLiteGraphStore

    Při recall_context() navíc:
    - Dotáže graph na relevantní entity
    - Připojí vztahový kontext k sémantickému kontextu z paměti
    """

    def __init__(self, config: dict = None):
        if config is None:
            try:
                from config import CONFIG
                config = CONFIG
            except Exception:
                config = {}
        self.config = config
        self._use_llm_extract = config.get("graph_extraction_enabled", True)

        # Inicializuj graph store
        db_dir  = Path(config.get("memory_dir", "memory_data"))
        db_dir.mkdir(parents=True, exist_ok=True)
        db_path = db_dir / "knowledge_graph.db"
        try:
            from memory_graph import SQLiteGraphStore
            self._graph = SQLiteGraphStore(db_path)
            logger.info(f"GraphRAG: SQLiteGraphStore @ {db_path}")
        except Exception as e:
            logger.warning(f"GraphRAG: nelze inicializovat graph store: {e}")
            self._graph = None

    # ── Extrakce a ukládání ───────────────────────────────────────

    def extract_and_store(self, user_text: str, assistant_text: str,
                          source: str = "conversation") -> int:
        """Extrahuje entity z konverzace a uloží do grafu. Vrátí počet uložených trojic."""
        if not self._graph:
            return 0

        combined = f"{user_text}\n{assistant_text}"
        triplets = heuristic_extract(combined)

        # LLM extrakce jen pro delší/komplexní texty
        if self._use_llm_extract and len(combined) > 100:
            try:
                llm_triplets = llm_extract(combined, self.config)
                triplets.extend(llm_triplets)
            except Exception as e:
                logger.debug(f"GraphRAG LLM extrakce přeskočena: {e}")

        # Deduplikace
        seen = set()
        unique = []
        for t in triplets:
            key = (t[0].lower(), t[1].lower(), t[2].lower())
            if key not in seen:
                seen.add(key)
                unique.append(t)

        ts = time.time()
        count = 0
        for subj, pred, obj in unique:
            try:
                self._graph.add_relation(subj, pred, obj, ts=ts, source=source)
                count += 1
                logger.debug(f"Graph: {subj!r} --[{pred}]--> {obj!r}")
            except Exception as e:
                logger.debug(f"Graph store selhalo: {e}")

        return count

    # ── Recall — graph kontext pro LLM ───────────────────────────

    def recall_graph_context(self, query: str, max_relations: int = 8) -> str:
        """
        Vrátí kontext z knowledge grafu relevantní pro dotaz.
        Formát: "Petr pracuje na projektu Alpha (ts: 2024-01-15, zdroj: conversation)"
        """
        if not self._graph:
            return ""
        try:
            rels = self._graph.query_relations_for_text(query, max_results=max_relations)
            if not rels:
                return ""
            lines = []
            for r in rels:
                conf = r.get("confidence", 1.0)
                conf_str = f" (jistota: {conf:.0%})" if conf < 0.9 else ""
                lines.append(f"• {r['subject']} {r['predicate']} {r['object']}{conf_str}")
            return "Znalostní kontext:\n" + "\n".join(lines)
        except Exception as e:
            logger.debug(f"GraphRAG recall selhal: {e}")
            return ""

    def stats(self) -> dict:
        if not self._graph:
            return {"available": False}
        try:
            with self._graph._lock:
                n_entities = self._graph._conn.execute(
                    "SELECT COUNT(*) as c FROM entities").fetchone()["c"]
                n_relations = self._graph._conn.execute(
                    "SELECT COUNT(*) as c FROM relations").fetchone()["c"]
            return {
                "available": True,
                "entities": n_entities,
                "relations": n_relations,
            }
        except Exception:
            return {"available": False}


# Singleton
_graph_rag: Optional[GraphRAGMemory] = None


def get_graph_rag(config: dict = None) -> GraphRAGMemory:
    global _graph_rag
    if _graph_rag is None:
        _graph_rag = GraphRAGMemory(config)
    return _graph_rag
