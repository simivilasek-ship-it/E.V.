import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from memory import JarvisMemory


class TestJarvisMemory(unittest.TestCase):
    @patch('memory.MemorySystem')
    @patch('memory.LocalProvider')
    def setUp(self, mock_local_provider, mock_memory_system):
        mock_memory_system.return_value = MagicMock()
        self.mem = JarvisMemory({})
        self.mem.system = MagicMock()

    def test_store(self):
        fake_memory = MagicMock(id='abc123')
        self.mem.system.store.return_value = fake_memory
        memory_id = self.mem.store('test content', importance=0.8)
        self.assertEqual(memory_id, 'abc123')
        self.mem.system.store.assert_called_once()

    def test_recall(self):
        fake_memory = MagicMock()
        fake_memory.memory.content = 'hello'
        fake_memory.memory.importance = 0.7
        fake_memory.memory.tags = ['test']
        fake_memory.memory.metadata = {}
        fake_memory.memory.created_at = None
        fake_memory.final_score = 0.85

        self.mem.system.recall.return_value = [fake_memory]
        results = self.mem.recall('hello')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['content'], 'hello')

    def test_recall_context(self):
        self.mem.recall = MagicMock(return_value=[{
            'content': 'User: test\nAI: odpověď',
            'tags': ['conversation'],
            'score': 0.8,
        }])
        context = self.mem.recall_context('test')
        self.assertIn('Previous:', context)

    def test_stats(self):
        stats = MagicMock(total_memories=5, avg_importance=0.45, by_category={})
        self.mem.system.stats.return_value = stats
        result = self.mem.stats()
        self.assertEqual(result['total_memories'], 5)
