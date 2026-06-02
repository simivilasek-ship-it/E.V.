import os
import pytest

pytestmark = [pytest.mark.unit]


def test_headless_denies_elevated_by_default(monkeypatch):
    """In headless mode (no GUI) ELEVATED actions should be denied by default."""
    # Ensure env var is not set
    monkeypatch.delenv("JARVIS_HEADLESS_APPROVE_ELEVATED", raising=False)
    from security_v2 import confirm_action

    assert confirm_action("delete_file", {}) is False


def test_headless_allows_elevated_with_env(monkeypatch):
    """If JARVIS_HEADLESS_APPROVE_ELEVATED is set, ELEVATED actions are auto-approved."""
    monkeypatch.setenv("JARVIS_HEADLESS_APPROVE_ELEVATED", "1")
    from security_v2 import confirm_action

    assert confirm_action("delete_file", {}) is True


def test_headless_denies_restricted_unknown_action(monkeypatch):
    """Unknown actions default to RESTRICTED and should be denied in headless."""
    monkeypatch.delenv("JARVIS_HEADLESS_APPROVE_ELEVATED", raising=False)
    from security_v2 import confirm_action

    # unknown action -> treated as RESTRICTED by confirm_action
    assert confirm_action("some_nonexistent_action_xyz", {}) is False
