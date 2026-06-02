import tempfile
from pathlib import Path
import time

from memory_graph import GraphStore


def test_add_and_query_graph_store(tmp_path):
    db = tmp_path / "graph.db"
    gs = GraphStore(db)

    # add simple relations
    gs.add_relation("Ty", "MÁ_BRATRA", "Jirka", ts=time.time(), source="heuristic", confidence=0.9)
    gs.add_relation("Jirka", "PROGRAMUJE_V", "Rust", ts=time.time()-1000, source="heuristic", confidence=0.8)

    # find entities
    res = gs.find_entities("Jirka")
    assert any(r['name'] == 'Jirka' for r in res)

    # query relations for text
    rels = gs.query_relations_for_text("můj brácha Jirka")
    assert any(r['predicate'] == 'MÁ_BRATRA' for r in rels)

    dump = gs.dump()
    assert 'nodes' in dump and 'links' in dump
