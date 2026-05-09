"""
JARVIS v2.0 — Konfigurace
Načítání a validace config.json
"""

import os
import json
from typing import Dict, Any

AVAILABLE_OLLAMA_MODELS = [
    "qwen2.5:3b",
    "llama3.1:8b",
    "llama3.2:3b",
    "mistral:7b",
    "deepseek-coder:latest",
    "qwen2.5-coder:1.5b-base",
]

DEFAULT_CONFIG = {
    "ollama_url": "http://localhost:11434/api/chat",
    "ollama_model": "qwen2.5:3b",   # výchozí — lepší než llama3.1:8b
    "tts_enabled": True,
    "tts_voice": "cs-CZ-AntoninNeural",
    "tts_rate": 170,
    "history_size": 20,
    "window_size": "560x760",
    "log_level": "INFO",
    "stt_timeout": 10,
    "stt_phrase_limit": 15,
    "stt_energy_threshold": 300,
}

def load_config() -> Dict[str, Any]:
    """Načte konfiguraci z config.json s validací"""
    config_path = os.path.join(os.path.dirname(__file__), "config.json")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
    except FileNotFoundError:
        user_config = {}
    except json.JSONDecodeError as e:
        raise ValueError(f"Neplatný config.json: {e}")

    # Sloučit s výchozími hodnotami
    config = {**DEFAULT_CONFIG, **user_config}

    # Validace
    _validate_config(config)

    return config

def _validate_config(config: Dict[str, Any]) -> None:
    """Validuje konfiguraci"""
    required_keys = ["ollama_url", "ollama_model"]
    for key in required_keys:
        if key not in config or not config[key]:
            raise ValueError(f"Chybí povinný klíč: {key}")

    if not isinstance(config["history_size"], int) or config["history_size"] < 1:
        raise ValueError("history_size musí být kladné celé číslo")

    if not isinstance(config["tts_enabled"], bool):
        raise ValueError("tts_enabled musí být boolean")

    if config["tts_rate"] < 50 or config["tts_rate"] > 400:
        raise ValueError("tts_rate musí být mezi 50-400")


def save_config(config: Dict[str, Any]) -> None:
    """Uloží aktuální konfiguraci do config.json."""
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


# Globální konfigurace
CONFIG = load_config()