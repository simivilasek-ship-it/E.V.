"""
JARVIS Config Schema — Pydantic v2 validation for config.json
Usage: from config_schema import JarvisSettings, validate_config
"""
from __future__ import annotations

import warnings
from typing import Any

from pydantic import BaseModel, Field, model_validator


class VoiceSettings(BaseModel):
    tts_enabled: bool = False
    tts_voice: str = "czech"
    tts_rate: int = Field(default=160, ge=50, le=400)
    stt_language: str = "cs-CZ"
    stt_energy_threshold: int = Field(default=300, ge=100, le=5000)
    wake_word_enabled: bool = False
    wake_word: str = "jarvis"
    duplex_audio_enabled: bool = False


class SecuritySettings(BaseModel):
    api_auth_required: bool = False
    api_bind_host: str = "127.0.0.1"
    api_bind_port: int = Field(default=8002, ge=1024, le=65535)

    @model_validator(mode="after")
    def warn_insecure(self) -> "SecuritySettings":
        if not self.api_auth_required and self.api_bind_host not in ("127.0.0.1", "localhost"):
            warnings.warn(
                "JARVIS: api_auth_required=False with non-localhost binding is insecure!",
                stacklevel=2,
            )
        return self


class AgentSettings(BaseModel):
    agent_max_steps: int = Field(default=10, ge=1, le=100)
    agent_timeout: int = Field(default=120, ge=10, le=3600)
    proactive_enabled: bool = True


class JarvisSettings(BaseModel):
    """Full validated JARVIS configuration."""

    ollama_url: str = "http://localhost:11434/api/chat"
    ollama_model: str = "qwen2.5:3b"
    history_size: int = Field(default=20, ge=1, le=200)
    voice: VoiceSettings = Field(default_factory=VoiceSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)

    model_config = {"extra": "allow"}  # allow unknown keys for forward-compat


def validate_config(cfg: dict[str, Any]) -> tuple[JarvisSettings, list[str]]:
    """
    Validate a config dict and return (settings, warnings_list).

    Never raises — returns a list of warning strings for invalid/notable values.
    The returned JarvisSettings falls back to defaults on validation errors.
    """
    warnings_list: list[str] = []
    try:
        flat = dict(cfg)

        # Partition flat keys into their sub-model buckets
        voice_keys = {k: flat.pop(k) for k in list(flat)
                      if k.startswith(("tts_", "stt_", "wake_", "duplex_"))}
        security_keys = {k: flat.pop(k) for k in list(flat) if k.startswith("api_")}
        agent_keys = {k: flat.pop(k) for k in list(flat) if k.startswith("agent_")}

        # proactive_enabled lives in AgentSettings but has no agent_ prefix
        if "proactive_enabled" in flat:
            agent_keys["proactive_enabled"] = flat.pop("proactive_enabled")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            settings = JarvisSettings(
                **flat,
                voice=VoiceSettings(**voice_keys),
                security=SecuritySettings(**security_keys),
                agent=AgentSettings(**agent_keys),
            )
        for w in caught:
            warnings_list.append(str(w.message))

        return settings, warnings_list

    except Exception as e:
        warnings_list.append(f"Config validation error: {e}")
        return JarvisSettings(), warnings_list
