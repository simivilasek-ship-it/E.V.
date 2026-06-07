"""Tests for optional LAN API token authentication middleware."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from config import CONFIG, DEFAULT_CONFIG
from src.api.middleware.auth import ApiTokenAuthMiddleware


@pytest.fixture
def auth_app():
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/api/health")
    def api_health():
        return {"ok": True}

    @app.get("/app")
    def web_app():
        return {"ui": True}

    @app.get("/api/protected")
    def protected():
        return {"data": "secret"}

    app.add_middleware(ApiTokenAuthMiddleware)
    return app


@pytest.fixture
def auth_enabled():
    saved = dict(CONFIG)
    CONFIG["api_auth_required"] = True
    CONFIG["api_token"] = "test-secret-token"
    yield
    CONFIG.clear()
    CONFIG.update(saved)


def test_health_exempt_when_auth_required(auth_app, auth_enabled):
    with patch("src.api.middleware.auth._is_localhost", return_value=False):
        client = TestClient(auth_app)
        assert client.get("/health").status_code == 200


def test_api_health_exempt_when_auth_required(auth_app, auth_enabled):
    with patch("src.api.middleware.auth._is_localhost", return_value=False):
        client = TestClient(auth_app)
        assert client.get("/api/health").status_code == 200


def test_app_static_exempt_when_auth_required(auth_app, auth_enabled):
    with patch("src.api.middleware.auth._is_localhost", return_value=False):
        client = TestClient(auth_app)
        assert client.get("/app").status_code == 200


def test_localhost_bypass(auth_app, auth_enabled):
    with patch("src.api.middleware.auth._is_localhost", return_value=True):
        client = TestClient(auth_app)
        assert client.get("/api/protected").status_code == 200


def test_remote_without_token_returns_401(auth_app, auth_enabled):
    with patch("src.api.middleware.auth._is_localhost", return_value=False):
        client = TestClient(auth_app)
        assert client.get("/api/protected").status_code == 401


def test_bearer_token_allows_remote_access(auth_app, auth_enabled):
    with patch("src.api.middleware.auth._is_localhost", return_value=False):
        client = TestClient(auth_app)
        r = client.get(
            "/api/protected",
            headers={"Authorization": "Bearer test-secret-token"},
        )
        assert r.status_code == 200
        assert r.json() == {"data": "secret"}


def test_x_jarvis_token_allows_remote_access(auth_app, auth_enabled):
    with patch("src.api.middleware.auth._is_localhost", return_value=False):
        client = TestClient(auth_app)
        r = client.get(
            "/api/protected",
            headers={"X-Jarvis-Token": "test-secret-token"},
        )
        assert r.status_code == 200


def test_wrong_token_returns_401(auth_app, auth_enabled):
    with patch("src.api.middleware.auth._is_localhost", return_value=False):
        client = TestClient(auth_app)
        r = client.get(
            "/api/protected",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert r.status_code == 401


def test_auth_disabled_allows_remote_without_token(auth_app):
    saved = dict(CONFIG)
    try:
        CONFIG["api_auth_required"] = False
        with patch("src.api.middleware.auth._is_localhost", return_value=False):
            client = TestClient(auth_app)
            assert client.get("/api/protected").status_code == 200
    finally:
        CONFIG.clear()
        CONFIG.update(saved)


def test_api_bind_host_default():
    assert DEFAULT_CONFIG["api_bind_host"] == "127.0.0.1"


def test_api_bind_host_from_env(monkeypatch):
    import config as config_module

    monkeypatch.setenv("JARVIS_BIND_HOST", "0.0.0.0")
    monkeypatch.setattr(config_module, "HAS_DOTENV", True)
    monkeypatch.setattr(
        config_module, "load_dotenv", lambda *a, **k: None, raising=False
    )
    monkeypatch.setattr(config_module.os.path, "exists", lambda p: True)
    env_config = config_module._load_env()
    assert env_config.get("api_bind_host") == "0.0.0.0"


def test_run_dashboard_uses_config_bind_host():
    saved = dict(CONFIG)
    try:
        CONFIG["api_bind_host"] = "127.0.0.1"
        with patch("src.api.app.uvicorn.run") as mock_run:
            from src.api.app import run_dashboard

            run_dashboard(port=8002)
            mock_run.assert_called_once()
            assert mock_run.call_args.kwargs["host"] == "127.0.0.1"
    finally:
        CONFIG.clear()
        CONFIG.update(saved)


def test_run_dashboard_warns_on_all_interfaces():
    saved = dict(CONFIG)
    try:
        CONFIG["api_bind_host"] = "0.0.0.0"
        with patch("src.api.app.uvicorn.run"), patch(
            "src.api.app.logger.warning"
        ) as mock_warn:
            from src.api.app import run_dashboard

            run_dashboard(port=8002)
            mock_warn.assert_called_once()
            assert "JARVIS_API_AUTH_REQUIRED=1" in mock_warn.call_args[0][0]
    finally:
        CONFIG.clear()
        CONFIG.update(saved)
