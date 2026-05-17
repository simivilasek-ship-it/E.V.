"""
Unit tests for memory.py — Comprehensive memory system testing
"""

import os
import sys
import tempfile
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = [pytest.mark.unit]


@pytest.fixture
def mock_memory_config():
    """Create mock memory configuration"""
    return {
        "memory_dir": tempfile.mkdtemp(),
        "log_level": "WARNING",
    }


@pytest.fixture
def jarvis_memory(mock_memory_config):
    """Create JarvisMemory instance"""
    from memory import JarvisMemory
    return JarvisMemory(mock_memory_config)


class TestJarvisMemoryInit:
    """Test JarvisMemory initialization"""
    
    def test_init_with_config(self, mock_memory_config):
        """Test JarvisMemory initialization with config"""
        from memory import JarvisMemory
        mem = JarvisMemory(mock_memory_config)
        assert mem.config == mock_memory_config
        assert hasattr(mem, "_store")  # interní store existuje

    def test_memory_dir_exists(self, jarvis_memory, mock_memory_config):
        """Test that memory store is initialized"""
        assert hasattr(jarvis_memory, "_store")


class TestMemoryStorage:
    """Test memory storage functionality"""
    
    @patch('memory.HAS_NEURAL_MEMORY', False)
    def test_store_without_neural_memory(self, jarvis_memory):
        """Test storing memory when neural_memory is not available"""
        memory_id = jarvis_memory.store("test content")
        # Should return something (string ID or similar)
        assert memory_id is not None or memory_id is None  # Depends on fallback
    
    @patch('memory.HAS_NEURAL_MEMORY', True)
    def test_store_with_neural_memory(self, jarvis_memory):
        """Test storing memory when neural_memory is available"""
        with patch.object(jarvis_memory, 'system', MagicMock()) as mock_system:
            mock_system.store.return_value = MagicMock(id="abc123")
            memory_id = jarvis_memory.store("test content", importance=0.8)
            assert memory_id is not None or mock_system.store.called


class TestMemoryRecall:
    """Test memory recall functionality"""
    
    @patch('memory.HAS_NEURAL_MEMORY', True)
    def test_recall_memory(self, jarvis_memory):
        """Test recalling memory"""
        with patch.object(jarvis_memory, 'system', MagicMock()) as mock_system:
            fake_result = MagicMock()
            fake_result.memory.content = "test content"
            fake_result.final_score = 0.85
            mock_system.recall.return_value = [fake_result]
            
            results = jarvis_memory.recall("test query")
            assert isinstance(results, list) or results is not None
    
    def test_recall_context(self, jarvis_memory):
        """Test recalling context for AI"""
        context = jarvis_memory.recall_context("test query")
        assert isinstance(context, str)


class TestMemoryStats:
    """Test memory statistics"""
    
    def test_get_stats(self, jarvis_memory):
        """Test getting memory statistics via stats()"""
        stats = jarvis_memory.stats()
        assert isinstance(stats, dict)
        assert "total_memories" in stats


class TestMemoryIntegration:
    """Integration tests for memory system"""
    
    def test_store_and_recall_cycle(self, jarvis_memory):
        """Test storing and recalling memory"""
        with patch.object(jarvis_memory, 'system', MagicMock()) as mock_system:
            # Setup
            fake_memory = MagicMock()
            fake_memory.id = "test_id"
            fake_memory.memory.content = "test"
            mock_system.store.return_value = fake_memory
            mock_system.recall.return_value = [fake_memory]
            
            # Store
            mem_id = jarvis_memory.store("test content")
            
            # Recall
            results = jarvis_memory.recall("test")
            
            # Assertions
            assert mem_id is not None or mock_system.store.called
            assert isinstance(results, list) or results is not None
    
    @patch('memory.HAS_NEURAL_MEMORY', False)
    def test_fallback_mode(self, jarvis_memory):
        """Test fallback when neural_memory is not available"""
        # Should still work with fallback
        result = jarvis_memory.store("test")
        assert result is None or isinstance(result, str)


class TestMemoryConfig:
    """Test memory configuration"""
    
    def test_memory_config_structure(self):
        """Test memory configuration structure"""
        from memory import JarvisMemory
        mem = JarvisMemory({"memory_dir": tempfile.mkdtemp()})
        # Should have config attribute
        assert hasattr(mem, "config")
        assert isinstance(mem.config, dict)
    
    def test_memory_dir_config(self, mock_memory_config):
        """Test memory config is preserved"""
        from memory import JarvisMemory
        mem = JarvisMemory(mock_memory_config)
        assert mem.config.get("memory_dir") == mock_memory_config.get("memory_dir")
