"""
JARVIS pytest configuration and fixtures
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from typing import Dict, Any
from unittest.mock import MagicMock, patch


@pytest.fixture(scope="session")
def test_config() -> Dict[str, Any]:
    """Test configuration"""
    return {
        "ollama_url": "http://localhost:11434/api/chat",
        "ollama_model": "qwen2.5:3b",
        "tts_enabled": False,  # Disable TTS in tests
        "stt_language": "cs-CZ",
        "log_level": "WARNING",
        "history_size": 5,
        "stt_energy_threshold": 300,
        "stt_timeout": 5,
    }


@pytest.fixture
def mock_config(test_config, monkeypatch):
    """Mock CONFIG from config.py"""
    # Create temp directory for test files
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        
        # Write test config
        with open(config_path, "w") as f:
            json.dump(test_config, f)
        
        # Patch CONFIG
        with patch("config.CONFIG", test_config):
            yield test_config


@pytest.fixture
def mock_logger(monkeypatch):
    """Mock logger to prevent actual logging during tests"""
    mock = MagicMock()
    monkeypatch.setattr("logging.getLogger", lambda *args, **kwargs: mock)
    return mock


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API response"""
    return {
        "model": "qwen2.5:3b",
        "created_at": "2024-01-01T00:00:00Z",
        "message": {
            "role": "assistant",
            "content": "This is a test response"
        },
        "done": True,
        "total_duration": 1000000000,  # nanoseconds
        "load_duration": 500000000,
        "prompt_eval_count": 10,
        "prompt_eval_duration": 300000000,
        "eval_count": 20,
        "eval_duration": 200000000,
    }


@pytest.fixture
def mock_permissions():
    """Mock security permissions"""
    return {
        "answer": "SAFE",
        "open_app": "SAFE",
        "delete_file": "ELEVATED",
        "shutdown": "ELEVATED",
    }


@pytest.fixture
def temp_memory_dir():
    """Create temporary memory directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_gui():
    """Mock GUI object"""
    mock = MagicMock()
    mock.root = MagicMock()
    mock._add_sys = MagicMock()
    mock._add_user = MagicMock()
    mock._add_assistant = MagicMock()
    return mock


@pytest.fixture
def mock_stt_engine(mock_config):
    """Mock STT engine"""
    mock = MagicMock()
    mock.listen = MagicMock(return_value="test command")
    mock.set_language = MagicMock(return_value=True)
    return mock


@pytest.fixture
def mock_tts_engine(mock_config):
    """Mock TTS engine"""
    mock = MagicMock()
    mock.speak = MagicMock()
    mock.stop = MagicMock()
    return mock


@pytest.fixture
def mock_llm_engine(mock_config, mock_ollama_response):
    """Mock LLM engine"""
    mock = MagicMock()
    mock.chat = MagicMock(return_value="AI response")
    mock.get_response = MagicMock(return_value=mock_ollama_response)
    return mock


@pytest.fixture
def sample_commands():
    """Sample command data for testing"""
    return {
        "open_app": {
            "action": "open_app",
            "app": "chrome",
        },
        "get_time": {
            "action": "get_time",
        },
        "set_volume": {
            "action": "volume",
            "level": 50,
        },
        "delete_file": {
            "action": "delete_file",
            "path": "/tmp/test.txt",
        },
    }


@pytest.fixture
def sample_user_commands():
    """Sample user input commands"""
    return [
        "Otevři Chrome",
        "Kolik je hodin?",
        "Nastav hlasitost na 50",
        "Smaž soubor test.txt",
        "Vypočítej 2+2*3",
        "Hledej Python na Wikipedii",
        "Zapamatuj si mám rád kávu",
    ]


# Markers for test categories
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line("markers", "unit: unit tests")
    config.addinivalue_line("markers", "integration: integration tests")
    config.addinivalue_line("markers", "slow: slow tests")
    config.addinivalue_line("markers", "requires_ollama: requires running Ollama")
    config.addinivalue_line("markers", "requires_mic: requires microphone")
    config.addinivalue_line("markers", "e2e: end-to-end tests with minimal mocks")


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    """FastAPI TestClient pro integrační / E2E API testy."""
    monkeypatch.setenv("JARVIS_TEST_MODE", "1")
    monkeypatch.setenv("JARVIS_ACTIVITY_DB", str(tmp_path / "activity.db"))
    monkeypatch.setenv("JARVIS_MISSIONS_DB", str(tmp_path / "missions.db"))

    import activity_store
    activity_store.reset_activity_store()

    from mission_manager import reset_mission_manager, set_db_path
    set_db_path(tmp_path / "missions.db")
    reset_mission_manager()
    try:
        from missions import reset_mission_store
        reset_mission_store()
    except Exception:
        pass

    try:
        from fastapi.testclient import TestClient
        from src.api.app import app
    except Exception as e:
        pytest.skip(f"FastAPI app unavailable: {e}")

    try:
        cm = TestClient(app, lifespan="off")
    except TypeError:
        cm = TestClient(app, raise_server_exceptions=False)
    with cm as client:
        yield client


# Autouse fixtures
@pytest.fixture(autouse=True)
def reset_modules():
    """Reset singleton state between tests to prevent test interference."""
    yield
    import importlib, sys
    try:
        import activity_store as _as
        _as.reset_activity_store()
    except Exception:
        pass
    try:
        from mission_manager import reset_mission_manager
        reset_mission_manager()
    except Exception:
        pass
    # Reset agent singletons
    for mod_name in ("agent_react", "agent_graph"):
        mod = sys.modules.get(mod_name)
        if mod:
            if hasattr(mod, "_agent"):
                mod._agent = None
            if hasattr(mod, "_graph"):
                mod._graph = None
    # Reset event bus singleton
    eb_mod = sys.modules.get("event_bus")
    if eb_mod and hasattr(eb_mod, "_bus"):
        try:
            if eb_mod._bus is not None:
                eb_mod._bus.stop(timeout=0.5)
        except Exception:
            pass
        eb_mod._bus = None
