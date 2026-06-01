"""
Testy pro ConversationSummarizer — context-aware memory pruning.
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch


def _make_memories(n: int) -> list:
    """Vytvoří seznam n fake konverzačních vzpomínek."""
    return [
        {
            "id": f"mem{i:03d}",
            "content": f"User: Otázka č.{i}\nAI: Odpověď č.{i}",
            "importance": 0.3,
            "tags": ["conversation"],
            "metadata": {"type": "conversation"},
            "created_at": time.time() - (n - i) * 3600,
            "score": 0.3,
        }
        for i in range(n)
    ]


def test_should_prune_false():
    """Méně zpráv než max_history → should_prune vrátí False."""
    from memory import ConversationSummarizer

    s = ConversationSummarizer({}, max_history=40)
    assert s.should_prune(0) is False
    assert s.should_prune(20) is False
    assert s.should_prune(39) is False


def test_should_prune_true():
    """Počet zpráv >= max_history → should_prune vrátí True."""
    from memory import ConversationSummarizer

    s = ConversationSummarizer({}, max_history=40)
    assert s.should_prune(40) is True
    assert s.should_prune(100) is True


def test_summarize_splits_correctly():
    """summarize_and_prune vrátí kratší seznam (první třetina odstraněna)."""
    from memory import ConversationSummarizer

    s = ConversationSummarizer({}, max_history=9)
    memories = _make_memories(9)

    # Mockujeme LLM — vždy vrátí ok summary
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {"message": {"content": "Uživatel se zajímá o Python."}}

    with patch("requests.post", return_value=mock_response):
        pruned, summary = s.summarize_and_prune(
            memories,
            ollama_url="http://localhost:11434/api/chat",
            model="qwen2.5:3b",
        )

    # 9 zpráv, split = 9 // 3 = 3 → pruned má 6 zpráv
    assert len(pruned) == 6
    assert summary == "Uživatel se zajímá o Python."


def test_prune_and_save_no_crash():
    """prune_and_save s mock memory_store + user_profile nepadne."""
    from memory import ConversationSummarizer

    s = ConversationSummarizer({}, max_history=10)
    memories = _make_memories(15)

    # Mock memory_store
    mock_store = MagicMock()
    mock_store.recall.return_value = memories

    # Mock user_profile
    mock_profile = MagicMock()

    # Mock LLM response
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {"message": {"content": "Shrnutí testovacích konverzací."}}

    with patch("requests.post", return_value=mock_response):
        result = s.prune_and_save(
            mock_store,
            mock_profile,
            ollama_url="http://localhost:11434/api/chat",
            model="qwen2.5:3b",
        )

    assert isinstance(result, str)
    assert "Zkondenzováno" in result
    # Ověř, že se pokusilo uložit souhrn do profilu
    mock_profile.set.assert_called_once_with(
        "conversation_summary",
        "Shrnutí testovacích konverzací.",
        confidence=0.9,
    )
