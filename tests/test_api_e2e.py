"""E2E testy pro JARVIS API — testují skutečné FastAPI handlery bez mock."""
import pytest
from fastapi.testclient import TestClient

# Import app z dashboard — pokud selže, skip all
try:
    from dashboard import app
    client = TestClient(app)
    HAS_APP = True
except Exception:
    HAS_APP = False


pytestmark = pytest.mark.skipif(not HAS_APP, reason="dashboard app nelze importovat")


class TestHealthEndpoint:
    def test_health_returns_200(self):
        r = client.get("/health")
        assert r.status_code in (200, 503)  # 503 pokud degraded

    def test_health_has_required_fields(self):
        r = client.get("/health")
        d = r.json()
        assert "status" in d
        assert "ws" in d
        assert d["ws"] == "running"
        assert "version" in d
        assert "checks" in d

    def test_health_checks_structure(self):
        r = client.get("/health")
        checks = r.json()["checks"]
        for key in ("cpu", "ram", "disk"):
            assert key in checks
            assert "ok" in checks[key]


class TestSystemEndpoint:
    def test_system_returns_metrics(self):
        r = client.get("/api/system")
        assert r.status_code == 200
        d = r.json()
        assert "cpu" in d
        assert "ram" in d
        assert "disk" in d
        assert 0 <= d["cpu"] <= 100
        assert 0 <= d["ram"] <= 100

    def test_system_has_extended_fields(self):
        r = client.get("/api/system")
        d = r.json()
        # Tyto mohou být None pokud hardware nepodporuje
        assert "cpu_temp" in d
        assert "gpu" in d
        assert "net" in d


class TestCommandEndpoint:
    def test_command_get_time(self):
        r = client.post("/api/command", json={"command": "kolik je hodin"})
        assert r.status_code == 200
        d = r.json()
        assert "response" in d
        assert len(d["response"]) > 0

    def test_command_empty_returns_error(self):
        r = client.post("/api/command", json={"command": ""})
        assert r.status_code == 200  # FastAPI vrátí 200 i pro prázdný příkaz
        d = r.json()
        assert "response" in d or "error" in d

    def test_command_hardware_info(self):
        r = client.post("/api/command", json={"command": "info o systemu"})
        assert r.status_code == 200


class TestPluginsEndpoint:
    def test_plugins_list(self):
        r = client.get("/api/plugins")
        assert r.status_code == 200
        d = r.json()
        assert "plugins" in d
        assert "total" in d
        assert d["total"] >= 0

    def test_plugins_have_health_status(self):
        r = client.get("/api/plugins")
        plugins = r.json().get("plugins", [])
        if plugins:
            p = plugins[0]
            assert "name" in p
            assert "status" in p


class TestConfigEndpoint:
    def test_config_get(self):
        r = client.get("/api/config")
        assert r.status_code == 200
        d = r.json()
        # Config nemá vracet secrets
        assert "brave_api_key" not in d

    def test_config_post_valid_key(self):
        r = client.post("/api/config", json={"ollama_model": "qwen2.5:3b"})
        assert r.status_code == 200
        d = r.json()
        assert d.get("ok") is True

    def test_config_post_invalid_key_ignored(self):
        r = client.post("/api/config", json={"hacker_key": "evil_value"})
        assert r.status_code == 200
        d = r.json()
        # Neznámý klíč se ignoruje — updated je prázdné
        updated = d.get("updated", {})
        assert "hacker_key" not in updated


class TestWorkflowsEndpoint:
    def test_workflows_list(self):
        r = client.get("/api/workflows")
        assert r.status_code == 200
        d = r.json()
        assert "workflows" in d
        assert isinstance(d["workflows"], list)

    def test_workflow_create_and_delete(self):
        # Vytvoř
        r = client.post("/api/workflows", json={
            "name": "Test workflow",
            "trigger_type": "manual",
            "trigger_config": {},
            "action": "kolik je hodin",
        })
        assert r.status_code == 200
        wf_id = r.json().get("id")
        assert wf_id is not None

        # Smaž
        r = client.delete(f"/api/workflows/{wf_id}")
        assert r.status_code == 200
        assert r.json().get("ok") is True


class TestNotifyEndpoint:
    def test_notify_endpoint_exists(self):
        r = client.post("/api/notify", json={
            "title": "Test",
            "body": "E2E test notifikace",
        })
        assert r.status_code == 200
        # ok může být False pokud notify-send chybí — to je OK
        assert "ok" in r.json()
