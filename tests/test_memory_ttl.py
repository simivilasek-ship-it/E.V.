"""Testy pro Memory TTL a priority funkce."""
import time, tempfile, pytest
from pathlib import Path
from unittest.mock import patch


def make_store():
    from memory import _SQLiteMemoryStore
    d = Path(tempfile.mkdtemp())
    return _SQLiteMemoryStore(d)


class TestMemoryTTL:

    def test_store_no_ttl_recalled(self):
        s = make_store()
        s.store("trvalá vzpomínka", 0.8, [], {}, ttl_seconds=0)
        results = s.recall("trvalá vzpomínka", 5, 0.0)
        assert any("trvalá" in r["content"] for r in results)

    def test_store_with_ttl_expired(self):
        s = make_store()
        s.store("rychle mizí", 0.9, [], {}, ttl_seconds=1)
        time.sleep(1.1)
        results = s.recall("rychle mizí", 5, 0.0)
        assert not any("rychle mizí" in r["content"] for r in results)

    def test_store_with_ttl_not_yet_expired(self):
        s = make_store()
        s.store("zatím tu je", 0.9, [], {}, ttl_seconds=60)
        results = s.recall("zatím tu je", 5, 0.0)
        assert any("zatím" in r["content"] for r in results)

    def test_priority_high_recalled(self):
        s = make_store()
        s.store("normální zpráva", 0.5, [], {}, priority=0)
        s.store("kritická zpráva", 0.5, [], {}, priority=2)
        results = s.recall("zpráva", 5, 0.0)
        assert len(results) >= 1
        assert results[0]["content"] == "kritická zpráva"

    def test_maintenance_deletes_expired(self):
        s = make_store()
        s.store("vyprší", 0.9, [], {}, ttl_seconds=1)
        s.store("zůstane", 0.9, [], {}, ttl_seconds=0)
        time.sleep(1.1)
        stats = s.run_maintenance()
        assert stats["deleted_expired"] == 1
        assert stats["total"] == 1

    def test_maintenance_no_expired(self):
        s = make_store()
        s.store("zůstane", 0.9, [], {})
        stats = s.run_maintenance()
        assert stats["deleted_expired"] == 0

    def test_stats_excludes_expired(self):
        s = make_store()
        s.store("živá", 0.9, [], {}, ttl_seconds=0)
        s.store("mrtvá", 0.9, [], {}, ttl_seconds=1)
        time.sleep(1.1)
        stats = s.stats()
        assert stats["total_memories"] == 1


class TestJarvisMemoryTTL:

    def test_jarvis_memory_store_ttl_passthrough(self):
        from memory import JarvisMemory
        with tempfile.TemporaryDirectory() as d:
            mem = JarvisMemory({"memory_dir": d})
            mid = mem.store("test", importance=0.8, ttl_seconds=60, priority=1)
            assert mid is not None
