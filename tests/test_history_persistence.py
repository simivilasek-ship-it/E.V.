"""
Testy pro Featura 1: Persist conversation history
Testuje save_history() a load_history() metody LLMEngine.
"""

import json
import os
import sys
import pytest
from collections import deque
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def minimal_config(tmp_path):
    """Minimální konfigurace pro LLMEngine bez síťových závislostí."""
    return {
        "ollama_url": "http://localhost:11434/api/chat",
        "ollama_model": "qwen2.5:3b",
        "history_size": 5,
    }


@pytest.fixture
def llm_engine(minimal_config, tmp_path):
    """LLMEngine s mock závislostmi — žádné síťové volání, žádný disk mimo tmp."""
    with (
        patch("llm.JarvisMemory", return_value=MagicMock()),
        patch("llm_router.LLMRouter", return_value=MagicMock()),
        patch("llm._router", MagicMock()),
    ):
        from llm import LLMEngine
        engine = LLMEngine(minimal_config)
        engine.history = deque(maxlen=minimal_config["history_size"])
        return engine


# ── Testy ────────────────────────────────────────────────────────────────────

def test_save_and_load_roundtrip(llm_engine, tmp_path):
    """Uložená historie se načte zpět se stejným obsahem."""
    history_path = tmp_path / "history.json"

    messages = [
        {"role": "user",      "content": "Ahoj E.V."},
        {"role": "assistant", "content": "Ahoj! Jak ti mohu pomoci?"},
        {"role": "user",      "content": "Kolik je hodin?"},
        {"role": "assistant", "content": "Nevím přesný čas."},
    ]
    for m in messages:
        llm_engine.history.append(m)

    llm_engine.save_history(path=str(history_path))
    assert history_path.exists(), "Soubor history.json musí existovat po save_history()"

    # Nová instance — načte uloženou historii
    llm_engine.history.clear()
    count = llm_engine.load_history(path=str(history_path))

    assert count == len(messages), f"Očekáváno {len(messages)} zpráv, načteno {count}"
    loaded = list(llm_engine.history)
    assert loaded == messages, "Načtené zprávy se musí shodovat s uloženými"


def test_load_nonexistent_returns_zero(llm_engine, tmp_path):
    """Načtení neexistujícího souboru vrátí 0 a nezpůsobí výjimku."""
    nonexistent = tmp_path / "neexistuje.json"
    count = llm_engine.load_history(path=str(nonexistent))
    assert count == 0, "Neexistující soubor musí vrátit 0"
    assert len(llm_engine.history) == 0, "Historie musí zůstat prázdná"


def test_invalid_messages_filtered(llm_engine, tmp_path):
    """Zprávy bez povinných polí role/content jsou přeskočeny."""
    history_path = tmp_path / "history_invalid.json"

    raw_data = [
        {"role": "user", "content": "Platná zpráva"},
        {"role": "assistant"},                          # chybí content
        {"content": "Chybí role"},                      # chybí role
        {"foo": "bar"},                                 # zcela neplatný
        {"role": "user", "content": "Druhá platná"},
    ]
    history_path.write_text(json.dumps(raw_data, ensure_ascii=False), encoding="utf-8")

    count = llm_engine.load_history(path=str(history_path))

    assert count == 2, f"Očekávány 2 platné zprávy, dostáno {count}"
    loaded = list(llm_engine.history)
    assert len(loaded) == 2
    assert loaded[0]["content"] == "Platná zpráva"
    assert loaded[1]["content"] == "Druhá platná"


def test_history_limited_to_maxlen(llm_engine, tmp_path):
    """Načtení více zpráv než maxlen ořízne na maxlen nejnovějších."""
    history_path = tmp_path / "history_big.json"
    maxlen = llm_engine.history.maxlen  # 5 podle minimal_config

    # Vytvoř 10 zpráv — víc než maxlen
    many_messages = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Zpráva {i}"}
        for i in range(10)
    ]
    history_path.write_text(json.dumps(many_messages, ensure_ascii=False), encoding="utf-8")

    count = llm_engine.load_history(path=str(history_path))

    # count vrací počet validních zpráv v souboru (10), ale history je oříznutá
    assert count == 10, f"Očekáváno 10 validních zpráv v souboru, dostáno {count}"
    assert len(llm_engine.history) == maxlen, (
        f"Historie musí být oříznutá na maxlen={maxlen}, má {len(llm_engine.history)}"
    )
    # Musíme mít POSLEDNÍCH maxlen zpráv (newest)
    loaded = list(llm_engine.history)
    expected = many_messages[-maxlen:]
    assert loaded == expected, "Musí být zachovány posledních maxlen zpráv"
