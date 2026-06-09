"""
Tests for config_schema.py — Pydantic v2 JARVIS config validation.
"""
import sys
import os
import warnings

import pytest

# Ensure project root is on the path when running directly
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config_schema import (
    JarvisSettings,
    VoiceSettings,
    SecuritySettings,
    AgentSettings,
    validate_config,
)


# ── JarvisSettings unit tests ─────────────────────────────────────────────


class TestJarvisSettingsDefaults:
    def test_default_model(self):
        s = JarvisSettings()
        assert s.ollama_model == "qwen2.5:3b"

    def test_default_history_size(self):
        s = JarvisSettings()
        assert s.history_size == 20

    def test_nested_voice_defaults(self):
        s = JarvisSettings()
        assert s.voice.tts_enabled is False
        assert s.voice.tts_rate == 160

    def test_nested_security_defaults(self):
        s = JarvisSettings()
        assert s.security.api_bind_host == "127.0.0.1"
        assert s.security.api_bind_port == 8002

    def test_nested_agent_defaults(self):
        s = JarvisSettings()
        assert s.agent.agent_max_steps == 10
        assert s.agent.agent_timeout == 120


class TestUnknownKeysAllowed:
    def test_extra_keys_do_not_raise(self):
        """extra='allow' means unknown keys are silently accepted."""
        s = JarvisSettings(
            ollama_model="llama3.1:8b",
            future_unknown_key="some_value",
            another_new_field=42,
        )
        assert s.ollama_model == "llama3.1:8b"
        # Pydantic v2 with extra='allow' stores extra fields as attributes
        assert s.future_unknown_key == "some_value"  # type: ignore[attr-defined]


# ── VoiceSettings validation ──────────────────────────────────────────────


class TestVoiceSettings:
    def test_valid_tts_rate(self):
        v = VoiceSettings(tts_rate=200)
        assert v.tts_rate == 200

    def test_tts_rate_too_low_raises(self):
        with pytest.raises(Exception):
            VoiceSettings(tts_rate=10)

    def test_tts_rate_too_high_raises(self):
        with pytest.raises(Exception):
            VoiceSettings(tts_rate=500)

    def test_stt_energy_threshold_bounds(self):
        v = VoiceSettings(stt_energy_threshold=100)
        assert v.stt_energy_threshold == 100
        with pytest.raises(Exception):
            VoiceSettings(stt_energy_threshold=99)
        with pytest.raises(Exception):
            VoiceSettings(stt_energy_threshold=5001)


# ── SecuritySettings validation ───────────────────────────────────────────


class TestSecuritySettings:
    def test_valid_port(self):
        s = SecuritySettings(api_bind_port=9000)
        assert s.api_bind_port == 9000

    def test_port_too_low_raises(self):
        with pytest.raises(Exception):
            SecuritySettings(api_bind_port=80)

    def test_port_too_high_raises(self):
        with pytest.raises(Exception):
            SecuritySettings(api_bind_port=70000)

    def test_insecure_binding_produces_warning(self):
        """api_auth_required=False + non-localhost host → UserWarning."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            SecuritySettings(api_auth_required=False, api_bind_host="0.0.0.0")
        assert any("insecure" in str(w.message).lower() for w in caught), \
            "Expected insecure-binding warning was not raised"

    def test_localhost_binding_no_warning(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            SecuritySettings(api_auth_required=False, api_bind_host="127.0.0.1")
        insecure = [w for w in caught if "insecure" in str(w.message).lower()]
        assert not insecure, "Unexpected insecure warning for localhost binding"

    def test_auth_required_no_warning_even_on_external_host(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            SecuritySettings(api_auth_required=True, api_bind_host="0.0.0.0")
        insecure = [w for w in caught if "insecure" in str(w.message).lower()]
        assert not insecure


# ── validate_config() integration ────────────────────────────────────────


class TestValidateConfig:
    def _minimal_config(self) -> dict:
        return {
            "ollama_url": "http://localhost:11434/api/chat",
            "ollama_model": "qwen2.5:3b",
            "history_size": 20,
        }

    def test_valid_config_passes(self):
        settings, warns = validate_config(self._minimal_config())
        assert isinstance(settings, JarvisSettings)
        assert settings.ollama_model == "qwen2.5:3b"
        assert warns == []

    def test_tts_keys_are_flattened_into_voice(self):
        cfg = {**self._minimal_config(), "tts_enabled": True, "tts_rate": 180}
        settings, warns = validate_config(cfg)
        assert settings.voice.tts_enabled is True
        assert settings.voice.tts_rate == 180
        assert warns == []

    def test_api_keys_are_flattened_into_security(self):
        cfg = {**self._minimal_config(), "api_bind_host": "127.0.0.1", "api_auth_required": True}
        settings, warns = validate_config(cfg)
        assert settings.security.api_auth_required is True
        assert warns == []

    def test_agent_keys_are_flattened_into_agent(self):
        cfg = {**self._minimal_config(), "agent_max_steps": 5, "agent_timeout": 60}
        settings, warns = validate_config(cfg)
        assert settings.agent.agent_max_steps == 5
        assert settings.agent.agent_timeout == 60
        assert warns == []

    def test_invalid_port_returns_warning_not_raise(self):
        cfg = {**self._minimal_config(), "api_bind_port": 80}
        settings, warns = validate_config(cfg)
        # Should not raise; warning or fallback to defaults expected
        assert isinstance(settings, JarvisSettings)
        assert len(warns) >= 1

    def test_insecure_binding_produces_warning_via_validate(self):
        cfg = {**self._minimal_config(), "api_auth_required": False, "api_bind_host": "0.0.0.0"}
        settings, warns = validate_config(cfg)
        assert isinstance(settings, JarvisSettings)
        insecure_warns = [w for w in warns if "insecure" in w.lower()]
        assert insecure_warns, f"No insecure warning found in: {warns}"

    def test_unknown_keys_allowed(self):
        cfg = {**self._minimal_config(), "future_feature": True, "custom_sites": {"moodle": "https://moodle.example.com"}}
        settings, warns = validate_config(cfg)
        assert isinstance(settings, JarvisSettings)
        assert warns == []

    def test_never_raises_on_garbage_input(self):
        settings, warns = validate_config({"ollama_model": None, "tts_rate": "not-a-number"})
        assert isinstance(settings, JarvisSettings)
        assert len(warns) >= 1

    def test_empty_config_uses_defaults(self):
        settings, warns = validate_config({})
        assert settings.ollama_model == "qwen2.5:3b"
        assert settings.history_size == 20
