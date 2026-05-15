"""
Testy pro EmbeddingEngine a integraci s memory recall().
Headless — nevyžadují sentence-transformers ani GPU.
"""

from __future__ import annotations
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Pomocné utility pro mock sentence_transformers
# ---------------------------------------------------------------------------

def _make_st_mock():
    """Vytvoří fake sentence_transformers modul."""
    st = types.ModuleType("sentence_transformers")
    class FakeST:
        def __init__(self, model_name):
            self.model_name = model_name
        def encode(self, text):
            import numpy as np
            # deterministický vektor podle délky textu
            return np.ones(16) * len(text)
    st.SentenceTransformer = FakeST
    return st


# ---------------------------------------------------------------------------
# Test 1 — init bez sentence-transformers → available=False
# ---------------------------------------------------------------------------

class TestEngineInitNoDeps(unittest.TestCase):
    def test_engine_init_no_deps(self):
        # Zajistíme, že sentence_transformers není dostupný
        with patch.dict(sys.modules, {"sentence_transformers": None}):
            # Re-import třídy s vypnutým modulem
            import importlib
            import memory as mem_mod
            # Odstraníme singleton aby se vytvořil nový engine
            original = mem_mod._embedding_engine
            mem_mod._embedding_engine = None
            try:
                engine = mem_mod.EmbeddingEngine()
                self.assertFalse(engine.available)
            finally:
                mem_mod._embedding_engine = original


# ---------------------------------------------------------------------------
# Test 2 — similarity fallback vrátí float 0–1
# ---------------------------------------------------------------------------

class TestSimilarityKeywordFallback(unittest.TestCase):
    def setUp(self):
        with patch.dict(sys.modules, {"sentence_transformers": None}):
            import memory as mem_mod
            self.engine = mem_mod.EmbeddingEngine()

    def test_similarity_keyword_fallback(self):
        score = self.engine.similarity("python programování", "javascript programování")
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)


# ---------------------------------------------------------------------------
# Test 3 — similarity identical strings (fallback) ≥ 0.99
# ---------------------------------------------------------------------------

class TestSimilarityIdentical(unittest.TestCase):
    def setUp(self):
        with patch.dict(sys.modules, {"sentence_transformers": None}):
            import memory as mem_mod
            self.engine = mem_mod.EmbeddingEngine()

    def test_similarity_identical(self):
        score = self.engine.similarity("ahoj", "ahoj")
        self.assertGreaterEqual(score, 0.99)


# ---------------------------------------------------------------------------
# Test 4 — encode bez modelu vrátí []
# ---------------------------------------------------------------------------

class TestEncodeEmptyFallback(unittest.TestCase):
    def setUp(self):
        with patch.dict(sys.modules, {"sentence_transformers": None}):
            import memory as mem_mod
            self.engine = mem_mod.EmbeddingEngine()

    def test_encode_empty_fallback(self):
        result = self.engine.encode("nějaký text")
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# Test 5 — recall volá similarity pokud je engine available
# ---------------------------------------------------------------------------

class TestRecallUsesSimilarity(unittest.TestCase):
    def test_recall_uses_similarity(self):
        import memory as mem_mod

        # Vytvoříme mock engine s available=True
        mock_engine = MagicMock()
        mock_engine.available = True
        mock_engine.similarity.return_value = 0.8

        with patch("memory.get_embedding_engine", return_value=mock_engine):
            import tempfile, pathlib
            with tempfile.TemporaryDirectory() as tmp:
                store = mem_mod._SQLiteMemoryStore(pathlib.Path(tmp))
                store.store("testovací obsah paměti", 0.7, ["tag"], {})
                results = store.recall("testovací dotaz", top_k=5, min_importance=0.0)

        mock_engine.similarity.assert_called()


# ---------------------------------------------------------------------------
# Test 6 — recall vrací výsledky seřazené podle score desc
# ---------------------------------------------------------------------------

class TestRecallReturnsSorted(unittest.TestCase):
    def test_recall_returns_sorted(self):
        import memory as mem_mod
        import tempfile, pathlib

        with patch.dict(sys.modules, {"sentence_transformers": None}):
            with tempfile.TemporaryDirectory() as tmp:
                store = mem_mod._SQLiteMemoryStore(pathlib.Path(tmp))
                store.store("python programování kód", 0.9, [], {})
                store.store("python skript nástroj kód", 0.5, [], {})
                store.store("python jazyk kód programování nástroj", 0.3, [], {})

                results = store.recall("python kód", top_k=10, min_importance=0.0)

        scores = [r["score"] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))


# ---------------------------------------------------------------------------
# Test 7 — recall vrátí max top_k výsledků
# ---------------------------------------------------------------------------

class TestRecallTopK(unittest.TestCase):
    def test_recall_top_k(self):
        import memory as mem_mod
        import tempfile, pathlib

        with patch.dict(sys.modules, {"sentence_transformers": None}):
            with tempfile.TemporaryDirectory() as tmp:
                store = mem_mod._SQLiteMemoryStore(pathlib.Path(tmp))
                for i in range(10):
                    store.store(f"python test obsah číslo {i}", 0.5, [], {})

                results = store.recall("python obsah", top_k=3, min_importance=0.0)

        self.assertLessEqual(len(results), 3)


# ---------------------------------------------------------------------------
# Test 8 — get_embedding_engine vrací singleton
# ---------------------------------------------------------------------------

class TestGetEmbeddingEngineSingleton(unittest.TestCase):
    def test_get_embedding_engine_singleton(self):
        import memory as mem_mod

        # Reset singletonu
        original = mem_mod._embedding_engine
        mem_mod._embedding_engine = None
        try:
            e1 = mem_mod.get_embedding_engine()
            e2 = mem_mod.get_embedding_engine()
            self.assertIs(e1, e2)
        finally:
            mem_mod._embedding_engine = original


if __name__ == "__main__":
    unittest.main()
