"""Tests for vision sandbox dry-run."""
from unittest.mock import MagicMock, patch

import vision_sandbox as vs


def test_preview_click_empty_target():
    out = vs.preview_click("")
    assert out["found"] is False


def test_execute_preview_cancelled():
    with patch.object(vs, "_previews", {"abc": vs.SandboxPreview(
        id="abc", target="btn", x=10, y=20, method="ocr", matched_text="OK",
        screenshot_b64="", screen_w=100, screen_h=100, created_at=vs.time.time(),
    )}):
        out = vs.execute_preview("abc", approved=False)
        assert out.get("cancelled") is True


def test_sandbox_enabled_reads_config():
    import config
    with patch.object(config, "CONFIG", {**config.CONFIG, "vision_sandbox_enabled": False}):
        assert vs.sandbox_enabled() is False


def test_click_with_sandbox_requires_approval():
    fake_preview = {
        "found": True, "id": "p1", "x": 5, "y": 6, "method": "ocr",
    }
    with patch.object(vs, "sandbox_enabled", return_value=True), \
         patch.object(vs, "auto_execute", return_value=False), \
         patch.object(vs, "preview_click", return_value=fake_preview):
        out = vs.click_with_sandbox("tlačítko OK")
        assert out.get("requires_approval") is True
        assert out.get("preview_id") == "p1"
