"""Regression tests: env names that Python actually reads, and invalid rebrand leftovers."""
from __future__ import annotations

from pathlib import Path

import pytest

import config as config_module

ROOT = Path(__file__).resolve().parents[1]

pytestmark = [pytest.mark.unit]

OPS_FILES = [
    "install.sh",
    "start.sh",
    "docker-compose.yml",
    "Dockerfile",
    ".github/workflows/test.yml",
    ".env.example",
]


def test_ops_files_do_not_use_invalid_ev_env_names():
    """`E.V._FOO` is not a valid bash identifier and os.environ.get never reads it."""
    offenders = []
    for rel in OPS_FILES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        if "E.V._" in text:
            offenders.append(rel)
    assert offenders == [], f"Invalid E.V._* names still in: {offenders}"


def test_install_sh_uses_valid_version_var():
    text = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "EV_VERSION=" in text
    assert "E.V._VERSION" not in text


def test_jarvis_bind_host_from_env(monkeypatch):
    """Process env is applied even when project .env is missing."""
    monkeypatch.setattr(config_module, "HAS_DOTENV", True)
    monkeypatch.setattr(config_module, "load_dotenv", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(config_module.os.path, "exists", lambda p: False)
    monkeypatch.setenv("JARVIS_BIND_HOST", "0.0.0.0")
    env_config = config_module._load_env()
    assert env_config.get("api_bind_host") == "0.0.0.0"


def test_jarvis_api_auth_required_from_env(monkeypatch):
    monkeypatch.setenv("JARVIS_API_AUTH_REQUIRED", "true")
    env_config = config_module._load_env()
    assert env_config.get("api_auth_required") is True


def test_jarvis_api_token_from_env(monkeypatch):
    monkeypatch.setenv("JARVIS_API_TOKEN", "secret-token")
    env_config = config_module._load_env()
    assert env_config.get("api_token") == "secret-token"


def test_load_env_works_without_dotenv_package(monkeypatch):
    monkeypatch.setattr(config_module, "HAS_DOTENV", False)
    monkeypatch.setenv("JARVIS_BIND_HOST", "10.0.0.5")
    env_config = config_module._load_env()
    assert env_config.get("api_bind_host") == "10.0.0.5"


def test_invalid_numeric_env_ignored(monkeypatch):
    monkeypatch.setenv("TTS_RATE", "not-a-number")
    env_config = config_module._load_env()
    assert "tts_rate" not in env_config


def test_validate_config_rejects_bad_history():
    cfg = {**config_module.DEFAULT_CONFIG, "history_size": 0}
    with pytest.raises(ValueError, match="history_size"):
        config_module._validate_config(cfg)


def test_validate_config_rejects_bad_tts_rate():
    cfg = {**config_module.DEFAULT_CONFIG, "tts_rate": 10}
    with pytest.raises(ValueError, match="tts_rate"):
        config_module._validate_config(cfg)
