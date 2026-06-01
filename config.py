"""
JARVIS — Konfigurace
Načítání a validace z .env, config.json s fallbackem na defaults
"""

__version__ = "4.5.0"

import os
import json
from typing import Dict, Any

try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

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
    "ollama_model": "qwen2.5:3b",
    "tts_enabled": True,
    "tts_voice": "cs-CZ-AntoninNeural",
    "tts_rate": 170,
    "history_size": 20,
    "window_size": "560x760",
    "log_level": "INFO",
    "log_file": "jarvis.log",
    "log_json_format": True,
    "stt_timeout": 10,
    "stt_phrase_limit": 15,
    "stt_energy_threshold": 300,
    "stt_language": "cs-CZ",
    "available_languages": {
        "cs-CZ": "Čeština",
        "en-US": "English (US)",
        "en-GB": "English (UK)",
        "es-ES": "Español",
        "fr-FR": "Français",
        "de-DE": "Deutsch",
        "it-IT": "Italiano",
        "pt-BR": "Português (BR)",
        "pl-PL": "Polski",
        "ru-RU": "Русский",
    },
    # Plugin systém
    "plugins_enabled": True,
    "disabled_plugins": [],
    "plugins_dir": "plugins",
    # Async engine
    "async_max_workers": 4,
    "async_max_queue": 100,
    # Error handling
    "max_error_log": 1000,
    "rate_limit_window": 60.0,
    "rate_limit_max": 10,
    # Security
    "audit_log_file": "audit.log",
    "audit_enabled": True,
    # Memory
    "memory_dir": "memory_data",
    # MCP defaults
    "mcp_filesystem_enabled": True,
    "mcp_git_enabled": True,
    "mcp_memory_enabled": True,
    "mcp_brave_enabled": False,
    "mcp_fetch_enabled": True,
    "mcp_playwright_enabled": False,
    "mcp_result_limit": 32_000,   # max znaků z MCP nástroje před zkrácením
    # Nové MCP servery v4.5
    "mcp_github_enabled": True,             # vyžaduje GITHUB_TOKEN v .env
    "mcp_sqlite_enabled": False,            # opt-in (JARVIS má vlastní memory API)
    "mcp_youtube_transcript_enabled": True, # bez API klíče
    "mcp_everything_enabled": False,        # opt-in desktop search
    "mcp_google_maps_enabled": True,        # vyžaduje GOOGLE_MAPS_API_KEY v .env
    "mcp_slack_enabled": True,              # vyžaduje SLACK_BOT_TOKEN v .env
    # Agent graph
    "agent_max_steps": 8,         # max Executor volání celkem
    "agent_max_retries": 2,       # max opakování jednoho kroku při chybě
    "agent_max_replans": 1,       # max přeplánování při záseknutí
    "agent_timeout": 120,         # max celková doba běhu grafu v sekundách
    "agent_llm_tokens": 500,      # max tokenů na jeden LLM call v grafu
}


def _load_env() -> Dict[str, Any]:
    """
    Načte konfiguraci z .env souboru
    Vrátí slovník s env proměnnými
    """
    if not HAS_DOTENV:
        return {}
    
    # Hledej .env v aktuálním adresáři
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return {}
    
    load_dotenv(env_path, override=True)
    
    # Mapování env proměnných → config klíče
    env_mapping = {
        "OLLAMA_URL": "ollama_url",
        "OLLAMA_MODEL": "ollama_model",
        "TTS_ENABLED": ("tts_enabled", lambda x: x.lower() == "true"),
        "TTS_VOICE": "tts_voice",
        "TTS_RATE": ("tts_rate", int),
        "STT_LANGUAGE": "stt_language",
        "STT_ENERGY_THRESHOLD": ("stt_energy_threshold", int),
        "STT_TIMEOUT": ("stt_timeout", int),
        "STT_PHRASE_LIMIT": ("stt_phrase_limit", int),
        "WINDOW_SIZE": "window_size",
        "HISTORY_SIZE": ("history_size", int),
        "LOG_LEVEL": "log_level",
        "LOG_FILE": "log_file",
        "LOG_JSON_FORMAT": ("log_json_format", lambda x: x.lower() == "true"),
        "PLUGINS_ENABLED": ("plugins_enabled", lambda x: x.lower() == "true"),
        "PLUGINS_DIR": "plugins_dir",
        "ASYNC_MAX_WORKERS": ("async_max_workers", int),
        "ASYNC_MAX_QUEUE": ("async_max_queue", int),
        "MAX_ERROR_LOG": ("max_error_log", int),
        "RATE_LIMIT_WINDOW": ("rate_limit_window", float),
        "RATE_LIMIT_MAX": ("rate_limit_max", int),
        "AUDIT_LOG_FILE": "audit_log_file",
        "AUDIT_ENABLED": ("audit_enabled", lambda x: x.lower() == "true"),
        "MEMORY_DIR": "memory_dir",
        "BRAVE_API_KEY": "brave_api_key",
        "MCP_FILESYSTEM_ENABLED": ("mcp_filesystem_enabled", lambda x: x.lower() == "true"),
        "MCP_GIT_ENABLED":        ("mcp_git_enabled",        lambda x: x.lower() == "true"),
        "MCP_MEMORY_ENABLED":     ("mcp_memory_enabled",     lambda x: x.lower() == "true"),
        "MCP_BRAVE_ENABLED":      ("mcp_brave_enabled",      lambda x: x.lower() == "true"),
        "MCP_FETCH_ENABLED":      ("mcp_fetch_enabled",      lambda x: x.lower() == "true"),
        "MCP_PLAYWRIGHT_ENABLED": ("mcp_playwright_enabled", lambda x: x.lower() == "true"),
    }
    
    config = {}
    for env_key, config_key in env_mapping.items():
        value = os.getenv(env_key)
        if value is None:
            continue
        
        # Zjisti config key a converter
        if isinstance(config_key, tuple):
            key, converter = config_key
            try:
                config[key] = converter(value)
            except (ValueError, TypeError):
                pass  # Ignoruj neplatné hodnoty
        else:
            config[config_key] = value
    
    return config


def _load_json_config() -> Dict[str, Any]:
    """Načte konfiguraci z config.json"""
    config_path = os.path.join(os.path.dirname(__file__), "config.json")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        raise ValueError(f"Neplatný config.json: {e}")


def load_config() -> Dict[str, Any]:
    """
    Načte konfiguraci v pořadí (priorita):
    1. .env soubor (environment variables — nejvyšší priorita)
    2. config.json soubor
    3. DEFAULT_CONFIG (fallback)
    """
    # Začni s defaults
    config = {**DEFAULT_CONFIG}
    
    # Aplikuj JSON konfiguraci
    json_config = _load_json_config()
    config.update(json_config)
    
    # Aplikuj ENV konfiguraci (nejvyšší priorita)
    env_config = _load_env()
    config.update(env_config)
    
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

    if config["stt_energy_threshold"] < 100 or config["stt_energy_threshold"] > 4000:
        raise ValueError("stt_energy_threshold musí být mezi 100-4000")


def save_config(config: Dict[str, Any]) -> None:
    """Uloží aktuální konfiguraci do config.json."""
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


# Globální konfigurace
CONFIG = load_config()