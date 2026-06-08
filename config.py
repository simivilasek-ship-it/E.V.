"""
JARVIS — Konfigurace
Načítání a validace z .env, config.json s fallbackem na defaults
"""

__version__ = "5.11.0"

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
    "vision_model": "llava:7b",
    "web_mode": False,
    "missions_enabled": True,
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
    "api_bind_host": "127.0.0.1",
    "api_token": "",
    "api_auth_required": False,
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
    # Proactive engine
    "proactive_enabled": True,
    "proactive_daily_time": "18:00",
    "proactive_workspace_roots": [],
    "proactive_poll_interval": 2.0,
    "proactive_max_notify_interval": 3600,  # seconds between notifications per file
    "proactive_report_retention_days": 30,
    "proactive_require_permission": False,  # if True, Proactive will check SecurityManager before file/git ops
    "proactive_max_files_scan": 2000,

    # Computer Use (Accessibility / UI Automation)
    "computer_use_enabled": False,
    "computer_use_backend": "auto",  # auto|windows_uia|macos_ax|linux_atspi

    # Live audio / duplex
    "audio_ws_enabled": True,
    "audio_ws_tts": True,
    "vad_enabled": True,
    "vad_mode": "auto",  # auto|webrtcvad|rms
    "vad_sample_rate": 16000,
    "duplex_audio_enabled": False,

    # Vision sandbox (dry-run před kliknutím)
    "vision_sandbox_enabled": True,
    "vision_sandbox_auto_execute": False,

    # Vision pipeline
    "vision_gpu_enabled": False,
    "vision_cache_enabled": True,
    "vision_cache_dir": "~/.jarvis/vision_cache",
    "vision_low_end_mode": False,

    # Knowledge Graph extraction
    "graph_extraction_enabled": True,
    # Graph backend note (MVP: sqlite local store). Possible values: sqlite_mvp|neo4j|memgraph
    "graph_backend": "sqlite_mvp",
    # automatic merging for memory graph (MVP conservative)
    "memory_graph_auto_merge": False,
    "memory_graph_merge_threshold": 0.88,
    "memory_graph_timeline": True,

    # MCP auto-install (MVP: only suggestions, installer not automatic)
    "mcp_auto_install_enabled": False,

    # Plugin marketplace features
    "marketplace_enable_ratings": True,
    "marketplace_enable_screenshots": True,

    # Whisper Live (real-time duplex STT)
    "whisper_model_size": "base",      # tiny | base | small | medium | large
    "whisper_live_enabled": True,      # False = fallback na původní Google STT
    # Duplex audio
    "duplex_barge_in": True,           # přerušení TTS řečí

    # Autonomous Workers (email, git, calendar, slack, github)
    "autonomous_workers_enabled": True,
    "auto_workers_interval": 900,   # sekundy mezi kontrolami (15 min)
    "imap_host": "",                # nebo IMAP_HOST v .env
    "imap_user": "",                # nebo IMAP_USER v .env
    "imap_pass": "",                # nebo IMAP_PASS v .env
    "calendar_ical_url": "",        # nebo CALENDAR_ICAL_URL v .env
    "slack_bot_token": "",          # nebo SLACK_BOT_TOKEN v .env
    "github_token": "",             # nebo GITHUB_TOKEN v .env

    # Cloud Routing (Groq / OpenRouter)
    "cloud_routing_enabled": True,
    # threshold: 'complex' = cloud jen pro kód/reasoning/agenty (doporučeno)
    #            'always'  = vždy cloud (Ollama = fallback)
    #            'simple'  = cloud jen pro rychlé dotazy
    "cloud_routing_threshold": "complex",
    "groq_api_key": "",           # nebo GROQ_API_KEY v .env
    "openrouter_api_key": "",     # nebo OPENROUTER_API_KEY v .env

    # Shadow Mode (developer assistant)
    "shadow_mode_enabled": False,
    # shadow_mode_level: 'suggestions' = read-only suggestions, 'autofix' = attempt fixes (ELEVATED)
    "shadow_mode_level": "suggestions",
    "shadow_mode_workspace_roots": [],
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
        "JARVIS_BIND_HOST": "api_bind_host",
        "JARVIS_API_TOKEN": "api_token",
        "JARVIS_API_AUTH_REQUIRED": (
            "api_auth_required",
            lambda x: x.lower() in ("1", "true", "yes"),
        ),
        "MEMORY_DIR": "memory_dir",
        "BRAVE_API_KEY": "brave_api_key",
        "GROQ_API_KEY": "groq_api_key",
        "OPENROUTER_API_KEY": "openrouter_api_key",
        "CLOUD_ROUTING_ENABLED": ("cloud_routing_enabled", lambda x: x.lower() == "true"),
        "CLOUD_ROUTING_THRESHOLD": "cloud_routing_threshold",
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