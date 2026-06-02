import pytest


@pytest.mark.timeout(5)
def test_import_dashboard_app():
    # Smoke: module imports and exposes FastAPI app
    import dashboard

    assert hasattr(dashboard, "app")


@pytest.mark.timeout(5)
def test_debug_bundle_endpoint_exists():
    from fastapi.testclient import TestClient
    from dashboard import app

    c = TestClient(app)
    r = c.get("/api/debug/bundle")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/zip")

