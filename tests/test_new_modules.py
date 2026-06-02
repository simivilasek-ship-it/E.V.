"""
Unit tests for new modules — health_check, cache_manager, offline_mode
"""

import pytest
import tempfile
from unittest.mock import MagicMock, patch
from pathlib import Path

pytestmark = [pytest.mark.unit]


# ════════════════════════════════════════════════════════
# HEALTH CHECK TESTS
# ════════════════════════════════════════════════════════

class TestHealthChecker:
    """Test HealthChecker system"""
    
    @pytest.fixture
    def health_checker(self, mock_config):
        """Create HealthChecker instance"""
        from health_check import HealthChecker
        return HealthChecker(mock_config)
    
    def test_health_checker_init(self, health_checker):
        """Test HealthChecker initialization"""
        assert health_checker is not None
        assert len(health_checker._checks) > 0
    
    def test_register_check(self, health_checker):
        """Test registering custom health check"""
        def custom_check():
            from health_check import HealthCheckResult, HealthStatus
            return HealthCheckResult(
                component="custom",
                status=HealthStatus.HEALTHY,
                message="Custom check OK"
            )
        
        health_checker.register_check("custom", custom_check)
        assert "custom" in health_checker._checks
    
    def test_check_all(self, health_checker):
        """Test running all health checks"""
        results = health_checker.check_all()
        assert isinstance(results, dict)
        assert len(results) > 0
    
    def test_get_status(self, health_checker):
        """Test getting overall status"""
        from health_check import HealthStatus
        status = health_checker.get_status()
        assert status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY, HealthStatus.UNKNOWN]
    
    def test_get_results(self, health_checker):
        """Test retrieving health check results"""
        health_checker.check_all()
        results = health_checker.get_results(limit=10)
        assert isinstance(results, list)


# ════════════════════════════════════════════════════════
# CACHE MANAGER TESTS
# ════════════════════════════════════════════════════════

class TestMemoryCache:
    """Test MemoryCache backend"""
    
    @pytest.fixture
    def memory_cache(self):
        """Create MemoryCache instance"""
        from cache_manager import MemoryCache
        return MemoryCache(max_size=100)
    
    def test_cache_set_get(self, memory_cache):
        """Test setting and getting cache"""
        memory_cache.set("key1", "value1")
        assert memory_cache.get("key1") == "value1"
    
    def test_cache_not_found(self, memory_cache):
        """Test getting non-existent key"""
        assert memory_cache.get("nonexistent") is None
    
    def test_cache_delete(self, memory_cache):
        """Test deleting cache entry"""
        memory_cache.set("key1", "value1")
        memory_cache.delete("key1")
        assert memory_cache.get("key1") is None
    
    def test_cache_ttl(self, memory_cache):
        """Test cache expiration"""
        memory_cache.set("key1", "value1", ttl=1)
        assert memory_cache.get("key1") == "value1"
        
        import time
        time.sleep(1.1)
        assert memory_cache.get("key1") is None
    
    def test_cache_stats(self, memory_cache):
        """Test cache statistics"""
        memory_cache.set("key1", "value1")
        memory_cache.get("key1")
        
        stats = memory_cache.stats()
        assert "size" in stats
        assert "max_size" in stats


class TestDiskCache:
    """Test DiskCache backend"""
    
    @pytest.fixture
    def disk_cache(self):
        """Create DiskCache instance"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from cache_manager import DiskCache
            yield DiskCache(cache_dir=tmpdir)
    
    def test_disk_cache_set_get(self, disk_cache):
        """Test disk cache set/get"""
        disk_cache.set("key1", "value1")
        assert disk_cache.get("key1") == "value1"
    
    def test_disk_cache_delete(self, disk_cache):
        """Test disk cache delete"""
        disk_cache.set("key1", "value1")
        disk_cache.delete("key1")
        assert disk_cache.get("key1") is None


class TestCacheManager:
    """Test CacheManager"""
    
    @pytest.fixture
    def cache_manager(self):
        """Create CacheManager instance"""
        from cache_manager import CacheManager
        return CacheManager()
    
    def test_cache_manager_get_set(self, cache_manager):
        """Test cache manager get/set"""
        cache_manager.set("key1", "value1", backend="memory")
        assert cache_manager.get("key1", backend="memory") == "value1"
    
    def test_cache_manager_delete(self, cache_manager):
        """Test cache manager delete"""
        cache_manager.set("key1", "value1", backend="memory")
        cache_manager.delete("key1", backend="memory")
        assert cache_manager.get("key1", backend="memory") is None
    
    def test_cache_stats(self, cache_manager):
        """Test cache manager statistics"""
        cache_manager.set("key1", "value1")
        stats = cache_manager.get_stats()
        assert "memory" in stats


# ════════════════════════════════════════════════════════
# OFFLINE MODE TESTS
# ════════════════════════════════════════════════════════

class TestOfflineManager:
    """Test OfflineManager"""
    
    @pytest.fixture
    def offline_manager(self, mock_config, tmp_path):
        """Create OfflineManager instance with tmp dir to avoid slow disk I/O."""
        from offline_mode import OfflineManager
        from unittest.mock import patch
        cfg = {**mock_config, "offline_cache_dir": str(tmp_path)}
        with patch.object(OfflineManager, "_persist_queue", return_value=None):
            mgr = OfflineManager(cfg)
        mgr._persist_queue = lambda: None  # no-op for all subsequent calls
        return mgr
    
    def test_offline_manager_init(self, offline_manager):
        """Test OfflineManager initialization"""
        from offline_mode import OfflineStatus
        assert offline_manager.get_status() == OfflineStatus.ONLINE
    
    def test_set_offline_status(self, offline_manager):
        """Test setting offline status"""
        from offline_mode import OfflineStatus
        offline_manager.set_status(OfflineStatus.OFFLINE)
        assert offline_manager.get_status() == OfflineStatus.OFFLINE
    
    def test_queue_command(self, offline_manager):
        """Test queueing command"""
        cmd_id = offline_manager.queue_command("test_action", {"param": "value"})
        assert cmd_id is not None
        assert isinstance(cmd_id, str)
    
    def test_get_offline_response(self, offline_manager):
        """Test getting offline response"""
        response = offline_manager.get_offline_response("Kolik je hodin?")
        assert response is not None
        assert isinstance(response, str)
        
    def test_get_offline_response_normalized(self, offline_manager):
        """Test getting offline response with diacritics and casing variation"""
        response1 = offline_manager.get_offline_response("cas?")
        response2 = offline_manager.get_offline_response("Co je Python?")
        assert "Čas" in response1 or "Time" in response1 or "offline" in response1.lower()
        assert "Python" in response2
    
    def test_sync_commands(self, offline_manager, tmp_path):
        """Test syncing queued commands"""
        import pytest
        offline_manager.queue_command("test", {"param": "value"})

        synced = []

        def mock_sync(action, params):
            synced.append(action)
            return True

        stats = offline_manager.sync_commands(mock_sync)
        assert "total" in stats
        assert "synced" in stats
        assert stats["total"] >= 1


class TestOfflineLLMFallback:
    """Test OfflineLLMFallback"""
    
    @pytest.fixture
    def offline_llm(self, mock_config):
        """Create OfflineLLMFallback instance"""
        from offline_mode import OfflineLLMFallback
        return OfflineLLMFallback(mock_config)
    
    def test_offline_llm_chat_online(self, offline_llm):
        """Test chat when online"""
        result = offline_llm.chat("Hello")
        # Online mode should return None (fallback not needed)
        assert result is None
    
    def test_offline_llm_fallback(self, offline_llm):
        """Test offline fallback"""
        from offline_mode import OfflineStatus
        offline_llm.offline_manager.set_status(OfflineStatus.OFFLINE)
        
        result = offline_llm.chat("Kolik je hodin?")
        assert result is not None
        assert isinstance(result, str)
    
    def test_is_offline_mode(self, offline_llm):
        """Test checking offline mode"""
        from offline_mode import OfflineStatus
        
        assert offline_llm.is_offline_mode() is False
        
        offline_llm.offline_manager.set_status(OfflineStatus.OFFLINE)
        assert offline_llm.is_offline_mode() is True
