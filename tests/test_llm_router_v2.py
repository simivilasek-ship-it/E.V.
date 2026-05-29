"""
Tests for LLMRouter v2 — rozšířená detekce úkolů a model routing.
"""
from unittest.mock import patch, MagicMock
import pytest

from llm_router import LLMRouter, TaskType


DEFAULT_MODEL = "qwen2.5:3b"
OLLAMA_URL = "http://localhost:11434/api/chat"


@pytest.fixture
def router():
    return LLMRouter(OLLAMA_URL, DEFAULT_MODEL)


# ── Detekce typu úkolu ─────────────────────────────────────────────────────


def test_detect_vision_task(router):
    result = router.detect_task("co vidíš na obrazovce?")
    assert result == TaskType.VISION


def test_detect_code_task(router):
    result = router.detect_task("napiš python funkci pro řazení pole")
    assert result == TaskType.CODE


def test_detect_math_task(router):
    result = router.detect_task("vypočítej integrál sin(x) od 0 do pi")
    assert result == TaskType.MATH


def test_detect_reasoning(router):
    result = router.detect_task("porovnej výhody nevýhody SQL a NoSQL databází")
    assert result == TaskType.REASONING


def test_detect_fast(router):
    # Krátká fráze < 50 znaků s klíčovým slovem
    text = "přelož hello"
    assert len(text) < 50
    result = router.detect_task(text)
    assert result == TaskType.FAST


# ── Model fallback ─────────────────────────────────────────────────────────


def test_model_fallback(router):
    """Pokud preferovaný model není dostupný, vrátí default model."""
    # Simulujeme Ollama, která nevrací žádné modely — _get_available_models
    # pak vrátí {default_model}. Pro CODE task jsou preferovány
    # ["deepseek-coder:latest", "qwen2.5:7b", default_model] — první dva
    # nejsou v available, takže musí padnout na default_model.
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_resp.json.return_value = {"models": []}  # žádné modely
        mock_get.return_value = mock_resp

        # Vynuluj cache, aby se skutečně zavolal mock
        router._models_cache = set()
        router._models_cache_ts = 0.0
        router._available_cache = None
        router._cache_ts = 0.0

        model, temp, max_tok = router.get_model_for_task(TaskType.CODE)

    assert model == DEFAULT_MODEL
