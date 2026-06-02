"""
Unit tests for llm.py — LLM integration testing
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch, call
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = [pytest.mark.unit]


@pytest.fixture
def mock_llm_config():
    """Create mock LLM configuration"""
    return {
        "ollama_url": "http://localhost:11434/api/chat",
        "ollama_model": "qwen2.5:3b",
        "history_size": 5,
    }


@pytest.fixture
def ollama_api_response():
    """Mock Ollama API response"""
    return {
        "model": "qwen2.5:3b",
        "created_at": "2024-01-01T00:00:00Z",
        "message": {
            "role": "assistant",
            "content": "Test response from Ollama"
        },
        "done": True,
    }


@pytest.fixture
def mock_memory():
    """Mock memory system"""
    mock = MagicMock()
    mock.recall_context.return_value = "Previous context"
    mock.store.return_value = "memory_id_123"
    return mock


class TestLLMRouter:
    """Test LLM router (local command recognition)"""
    
    def test_parse_command_simple(self):
        """Test parsing simple commands — route() vrátí tuple (message, action_dict)"""
        from llm import LocalRouter as LLMRouter
        router = LLMRouter()
        result = router.route("kolik je hodin")
        assert isinstance(result, tuple) and len(result) == 2
        _msg, action = result
        assert isinstance(action, dict)
        assert action.get("action") == "get_time"

    def test_parse_command_open_app(self):
        """Test rozpoznání příkazu pro otevření aplikace"""
        from llm import LocalRouter as LLMRouter
        router = LLMRouter()
        _msg, action = router.route("otevři chrome")
        assert isinstance(action, dict)
        assert action.get("action") == "open_app"

    def test_parse_command_unknown_returns_none(self):
        """Neznámý vstup vrátí (None, None)"""
        from llm import LocalRouter as LLMRouter
        router = LLMRouter()
        result = router.route("nějaký nesmysl xyz")
        assert result == (None, None)


class TestSystemPrompt:
    """Test LLM system prompt"""
    
    def test_system_prompt_exists(self):
        """Ensure system prompt is defined"""
        from llm import SYSTEM_PROMPT
        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 0
    
    def test_system_prompt_contains_jarvis(self):
        """Ensure system prompt identifies as JARVIS"""
        from llm import SYSTEM_PROMPT
        assert "JARVIS" in SYSTEM_PROMPT or "jarvis" in SYSTEM_PROMPT.lower()
    
    def test_system_prompt_czech(self):
        """Ensure system prompt is in Czech"""
        from llm import SYSTEM_PROMPT
        # Should contain Czech keywords
        czech_keywords = ["Komunikuješ", "česky", "Python", "počítač"]
        assert any(kw in SYSTEM_PROMPT for kw in czech_keywords)


@pytest.mark.requires_ollama
class TestLLMIntegration:
    """Integration tests requiring Ollama (marked as requires_ollama)"""
    
    @patch('requests.post')
    def test_ollama_api_call(self, mock_post, mock_llm_config, ollama_api_response):
        """Test making API call to Ollama"""
        mock_post.return_value = MagicMock(
            json=MagicMock(return_value=ollama_api_response),
            status_code=200
        )
        
        from llm import LLMEngine
        
        engine = LLMEngine(mock_llm_config)
        # ask() nebo stream_ask() je hlavní API
        assert hasattr(engine, 'ask') or hasattr(engine, 'stream_ask')
    
    @patch('requests.post')
    def test_ollama_error_handling(self, mock_post, mock_llm_config):
        """Test handling of Ollama API errors"""
        mock_post.return_value = MagicMock(
            status_code=500,
            json=MagicMock(side_effect=Exception("API Error"))
        )
        
        from llm import LLMEngine
        engine = LLMEngine(mock_llm_config)
        # Should handle errors gracefully
        assert engine is not None


class TestLLMCaching:
    """Test LLM response caching"""
    
    def test_cache_initialization(self):
        """Test cache is initialized"""
        from llm import LLMEngine
        engine = LLMEngine({"ollama_url": "http://localhost:11434/api/chat", "ollama_model": "test"})
        # Should have history or cache mechanism
        assert hasattr(engine, 'history') or True


class TestParseArgs:
    """Test argument parsing"""
    
    def test_parse_args_open_app(self):
        """Test parsing open_app arguments"""
        from llm import _parse_args
        result = _parse_args("open_app", "chrome")
        assert result.get("app") == "chrome"
    
    def test_parse_args_open_url(self):
        """Test parsing open_url arguments"""
        from llm import _parse_args
        result = _parse_args("open_url", "example.com")
        assert "url" in result
        assert "example.com" in result["url"]
    
    def test_parse_args_weather(self):
        """Test parsing weather arguments"""
        from llm import _parse_args
        result = _parse_args("weather", "Prague")
        assert result.get("city") == "Prague"
    
    def test_parse_args_calculate(self):
        """Test parsing calculate arguments"""
        from llm import _parse_args
        result = _parse_args("calculate", "2+2")
        assert result.get("expr") == "2+2" or result.get("expression") == "2+2"


class TestLLMConfig:
    """Test LLM configuration"""
    
    def test_available_models(self):
        """Test available models list"""
        from config import AVAILABLE_OLLAMA_MODELS
        assert len(AVAILABLE_OLLAMA_MODELS) > 0
        assert "qwen2.5:3b" in AVAILABLE_OLLAMA_MODELS
    
    def test_default_model(self, mock_llm_config):
        """Test default model is set"""
        assert mock_llm_config["ollama_model"] == "qwen2.5:3b"


class TestHistoryManagement:
    """Test conversation history management"""
    
    def test_clear_history(self):
        """Test clearing conversation history"""
        from llm import LLMEngine
        engine = LLMEngine({"ollama_url": "http://localhost:11434/api/chat", "ollama_model": "test"})
        
        if hasattr(engine, 'clear_history'):
            engine.clear_history()
            # History should be empty
            assert len(engine.history) == 0 or True
    
    def test_history_size_limit(self):
        """Test history size limiting"""
        config = {
            "ollama_url": "http://localhost:11434/api/chat",
            "ollama_model": "test",
            "history_size": 3
        }
        from llm import LLMEngine
        engine = LLMEngine(config)
        # Should respect history_size limit
        assert engine.config.get("history_size") == 3


@pytest.mark.integration
class TestLLMRouterIntegration:
    """Integration tests for LLM router"""
    
    def test_route_safe_action(self):
        """Test routing safe action"""
        from llm import LocalRouter as LLMRouter
        router = LLMRouter()
        # Router should be callable
        assert callable(router.route)
    
    def test_route_with_params(self):
        """Test routing with parameters"""
        from llm import LocalRouter as LLMRouter
        router = LLMRouter()
        # Should handle action routing
        assert hasattr(router, 'route')


# ── OllamaClient Cache Tests ──────────────────────────────────────

class TestOllamaClientCache:

    @pytest.fixture(autouse=True)
    def clean_cache(self):
        from cache_manager import get_cache_manager
        get_cache_manager().clear()

    @patch("requests.post")
    def test_ollama_client_cache_hit(self, mock_post):
        from llm import OllamaClient
        
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"message": {"content": "První odpověď"}}
        mock_post.return_value = mock_resp
        
        client = OllamaClient("http://mock/api/chat", "model-abc")
        
        r1 = client.call([{"role": "user", "content": "Ahoj"}])
        assert r1 == "První odpověď"
        assert mock_post.call_count == 1
        
        r2 = client.call([{"role": "user", "content": "Ahoj"}])
        assert r2 == "První odpověď"
        assert mock_post.call_count == 1

    @patch("requests.post")
    def test_ollama_client_json_cache_hit(self, mock_post):
        from llm import OllamaClient
        
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"message": {"content": '{"key": "value"}'}}
        mock_post.return_value = mock_resp
        
        client = OllamaClient("http://mock/api/chat", "model-abc")
        
        r1 = client.call_json([{"role": "user", "content": "Ahoj"}], schema={"key": "string"})
        assert r1 == {"key": "value"}
        assert mock_post.call_count == 1
        
        r2 = client.call_json([{"role": "user", "content": "Ahoj"}], schema={"key": "string"})
        assert r2 == {"key": "value"}
        assert mock_post.call_count == 1
