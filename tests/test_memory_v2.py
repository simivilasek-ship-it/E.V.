"""
Tests for memory v2 features:
- Long-term memory scoring (access_score)
- get_long_term / promote_to_long_term
- compress_old_memories
- export/import roundtrip
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import pytest

# Make sure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory import _SQLiteMemoryStore, JarvisMemory


# ── Helpers ────────────────────────────────────────────


def make_store(tmp_path: Path) -> _SQLiteMemoryStore:
    return _SQLiteMemoryStore(tmp_path)


def make_jarvis(tmp_path: Path) -> JarvisMemory:
    """Return a JarvisMemory that always uses the SQLite fallback."""
    jm = object.__new__(JarvisMemory)
    jm.config = {}
    jm.system = None  # force SQLite path
    jm._store = _SQLiteMemoryStore(tmp_path)
    from memory import EpisodicMemory, ProceduralMemory
    jm.episodic = EpisodicMemory()
    jm.procedural = ProceduralMemory(tmp_path / "proc.json")
    return jm


# ══════════════════════════════════════════════════════
#  1. test_get_long_term_empty
# ══════════════════════════════════════════════════════


def test_get_long_term_empty(tmp_path):
    store = make_store(tmp_path)
    result = store.get_long_term()
    assert result == [], f"Očekáván prázdný seznam, ale dostali jsme: {result}"


# ══════════════════════════════════════════════════════
#  2. test_promote_to_long_term
# ══════════════════════════════════════════════════════


def test_promote_to_long_term(tmp_path):
    store = make_store(tmp_path)
    mid = store.store("testovací vzpomínka", 0.5, [], {})
    store.promote_to_long_term(mid)

    with store._lock, store._connect() as con:
        row = con.execute(
            "SELECT access_score FROM memories WHERE id=?", (mid,)
        ).fetchone()

    assert row is not None, "Vzpomínka nenalezena v DB"
    assert row["access_score"] == 10.0, f"Očekáváno 10.0, ale dostali jsme: {row['access_score']}"


# ══════════════════════════════════════════════════════
#  3. test_compress_too_few
# ══════════════════════════════════════════════════════


def test_compress_too_few(tmp_path):
    jm = make_jarvis(tmp_path)
    # Ulož pouze 2 staré vzpomínky (méně než minimum 3)
    past = time.time() - 30 * 86400  # 30 dní zpět
    for i in range(2):
        mid = jm._store.store(f"Stará vzpomínka {i}", 0.5, [], {})
        with jm._store._lock, jm._store._connect() as con:
            con.execute("UPDATE memories SET created_at=? WHERE id=?", (past, mid))
            con.commit()

    result = jm.compress_old_memories(days_old=7)
    assert "Příliš málo" in result, f"Neočekávaná zpráva: {result}"


# ══════════════════════════════════════════════════════
#  4. test_export_import_roundtrip
# ══════════════════════════════════════════════════════


def test_export_import_roundtrip(tmp_path):
    src = make_jarvis(tmp_path / "src")
    src.store("Obsah vzpomínky A", importance=0.7, tags=["test"], metadata={"x": 1})
    src.store("Obsah vzpomínky B", importance=0.4, tags=[], metadata={})

    export_file = str(tmp_path / "export.json")
    msg = src.export_memories(export_file)
    assert "Exportováno" in msg

    exported = json.loads(Path(export_file).read_text(encoding="utf-8"))
    assert len(exported) == 2, f"Očekávány 2 vzpomínky, dostali jsme {len(exported)}"

    dst = make_jarvis(tmp_path / "dst")
    msg2 = dst.import_memories(export_file)
    assert "Importováno 2/2" in msg2, f"Neočekávaná zpráva: {msg2}"

    contents = {m["content"] for m in dst.recall("Obsah", top_k=10, min_importance=0.0)}
    assert "Obsah vzpomínky A" in contents
    assert "Obsah vzpomínky B" in contents


# ══════════════════════════════════════════════════════
#  5. test_access_score_increases_on_recall
# ══════════════════════════════════════════════════════


def test_access_score_increases_on_recall(tmp_path):
    store = make_store(tmp_path)
    mid = store.store("python programování jazyk", 0.8, [], {})

    def get_score():
        with store._lock, store._connect() as con:
            row = con.execute(
                "SELECT access_score FROM memories WHERE id=?", (mid,)
            ).fetchone()
        return row["access_score"] if row else None

    score_before = get_score()
    assert score_before == 0.0

    store.recall("python programování", top_k=5, min_importance=0.0)

    score_after = get_score()
    assert score_after is not None
    assert score_after > score_before, (
        f"access_score by mělo vzrůst po recall, bylo {score_before}, je {score_after}"
    )
    assert abs(score_after - (score_before + 0.25)) < 1e-9, (
        f"Očekáván nárůst o 0.25, ale dostali jsme {score_after}"
    )


# ══════════════════════════════════════════════════════
#  6. test_long_term_survives_maintenance
# ══════════════════════════════════════════════════════


def test_long_term_survives_maintenance(tmp_path):
    store = make_store(tmp_path)

    # Normální vzpomínka (stará, nízká importance → smazána při maintenance)
    normal_id = store.store("Obyčejná krátkodobá vzpomínka", 0.05, [], {})
    past = time.time() - 365 * 86400  # rok zpět
    with store._lock, store._connect() as con:
        con.execute("UPDATE memories SET created_at=?, importance=0.05 WHERE id=?", (past, normal_id))
        con.commit()

    # Long-term vzpomínka (access_score >= 2)
    lt_id = store.store("Důležitá long-term vzpomínka", 0.05, [], {})
    with store._lock, store._connect() as con:
        con.execute(
            "UPDATE memories SET created_at=?, importance=0.05, access_score=2.5 WHERE id=?",
            (past, lt_id)
        )
        con.commit()

    store.maintenance(decay_rate=0.1, min_importance=0.05)

    def exists(mid):
        with store._lock, store._connect() as con:
            row = con.execute("SELECT id FROM memories WHERE id=?", (mid,)).fetchone()
        return row is not None

    assert not exists(normal_id), "Normální stará vzpomínka měla být smazána"
    assert exists(lt_id), "Long-term vzpomínka (access_score >= 2) měla přežít maintenance"
