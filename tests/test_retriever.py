from pathlib import Path
import time

from memory_graph import GraphStore


def test_simple_retrieval(tmp_path):
    db = tmp_path / "graph2.db"
    gs = GraphStore(db)
    gs.add_relation("Ty", "MÁ_RÁD", "pizza", ts=time.time(), source="user", confidence=0.95)
    gs.add_relation("Ty", "MÁ_RÁD", "kávu", ts=time.time()-3600*24, source="user", confidence=0.7)

    rels = gs.query_relations_for_text("mám rád pizza")
    assert any(r['object'].lower() == 'pizza' for r in rels)
