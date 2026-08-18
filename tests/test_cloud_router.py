"""Unit tests for CloudRouter routing decisions (no live API calls)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cloud_router import CloudRouter, CloudStats, get_cloud_router

pytestmark = [pytest.mark.unit]


def test_disabled_without_keys():
    router = CloudRouter({"cloud_routing_enabled": True})
    assert router.enabled is False
    assert router.should_use_cloud("code") is False


def test_threshold_complex(monkeypatch):
    monkeypatch.delenv("CLOUD_ROUTING_ENABLED", raising=False)
    router = CloudRouter({
        "cloud_routing_enabled": True,
        "groq_api_key": "gsk_test",
        "cloud_routing_threshold": "complex",
    })
    assert router.enabled is True
    assert router.should_use_cloud("code") is True
    assert router.should_use_cloud("reasoning") is True
    assert router.should_use_cloud("fast") is False
    assert router.should_use_cloud("chat") is False


def test_threshold_always_and_simple(monkeypatch):
    monkeypatch.delenv("CLOUD_ROUTING_ENABLED", raising=False)
    always = CloudRouter({
        "cloud_routing_enabled": True,
        "groq_api_key": "gsk_test",
        "cloud_routing_threshold": "always",
    })
    assert always.should_use_cloud("anything") is True

    simple = CloudRouter({
        "cloud_routing_enabled": True,
        "groq_api_key": "gsk_test",
        "cloud_routing_threshold": "simple",
    })
    assert simple.should_use_cloud("fast") is True
    assert simple.should_use_cloud("code") is False


def test_env_disables_routing(monkeypatch):
    monkeypatch.setenv("CLOUD_ROUTING_ENABLED", "false")
    router = CloudRouter({"cloud_routing_enabled": True, "groq_api_key": "gsk_test"})
    assert router.enabled is False


def test_stats_and_groq_model():
    router = CloudRouter({"cloud_routing_enabled": True, "groq_api_key": "gsk_test"})
    stats = router.stats()
    assert stats["groq_available"] is True
    assert stats["total_calls"] == 0
    assert "llama" in router._groq_model("code")


def test_call_records_groq_success(monkeypatch):
    monkeypatch.delenv("CLOUD_ROUTING_ENABLED", raising=False)
    router = CloudRouter({"cloud_routing_enabled": True, "groq_api_key": "gsk_test"})
    fake = MagicMock()
    fake.content = "ok"
    fake.tokens_used = 3
    with patch.object(router, "_call_groq", return_value=fake):
        result = router.call([{"role": "user", "content": "hi"}])
    assert result.content == "ok"
    assert router.stats()["total_calls"] == 1


def test_call_raises_when_all_fail(monkeypatch):
    monkeypatch.delenv("CLOUD_ROUTING_ENABLED", raising=False)
    router = CloudRouter({"cloud_routing_enabled": True, "groq_api_key": "gsk_test"})
    with patch.object(router, "_call_groq", side_effect=RuntimeError("nope")):
        with pytest.raises(RuntimeError, match="cloud providery"):
            router.call([{"role": "user", "content": "hi"}])


def test_cloud_stats_avg():
    s = CloudStats()
    assert s.avg_latency() == 0.0
    s.record("groq", 100, 10)
    s.record("groq", 50, 5)
    assert s.avg_latency() == 75.0
    assert s.tokens == 15


def test_get_cloud_router_singleton(monkeypatch):
    import cloud_router as cr
    cr._cloud_router = None
    monkeypatch.delenv("CLOUD_ROUTING_ENABLED", raising=False)
    a = get_cloud_router({"cloud_routing_enabled": False})
    b = get_cloud_router({"cloud_routing_enabled": True, "groq_api_key": "x"})
    assert a is b
    cr._cloud_router = None
