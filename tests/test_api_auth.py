"""Tests for optional LAN API token authentication middleware."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from config import CONFIG
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
