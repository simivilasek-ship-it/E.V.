"""Unit tests for autonomous background workers (no live IMAP/Slack)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autonomous_workers import (
    BaseWorker,
    CalendarWorker,
    EmailWorker,
    GitWorker,
    WorkerEvent,
    WorkerManager,
    get_worker_manager,
)

pytestmark = [pytest.mark.unit]


def test_base_worker_unconfigured_run_is_empty():
    w = BaseWorker({})
    assert w.is_configured() is False
    assert w.run() == []
    assert w.should_run() is True


def test_email_worker_needs_credentials():
    w = EmailWorker({})
    assert w.is_configured() is False
    w = EmailWorker({"imap_host": "imap.example", "imap_user": "a", "imap_pass": "b"})
    assert w.is_configured() is True


def test_calendar_worker_needs_url():
    assert CalendarWorker({}).is_configured() is False
    assert CalendarWorker({"calendar_ical_url": "https://example/cal.ics"}).is_configured() is True


def test_git_worker_finds_nested_repo(tmp_path):
    repo = tmp_path / "proj"
    (repo / ".git").mkdir(parents=True)
    w = GitWorker({"proactive_workspace_roots": [str(tmp_path)]})
    assert w.is_configured() is True
    found = w._find_git_repos(str(tmp_path))
    assert str(repo) in found


def test_worker_manager_status_and_dispatch():
    mgr = WorkerManager({"proactive_workspace_roots": []}, on_notify=MagicMock())
    st = mgr.status()
    assert "running" in st
    assert "workers" in st
    assert any(w["name"] == "git" for w in st["workers"])
    mgr._dispatch(WorkerEvent(source="git", title="t", body="b", urgency="low", action_hint="hint"))
    mgr._notify.assert_called_once()
    assert "GIT" in mgr._notify.call_args[0][0]


def test_run_now_unknown_worker():
    mgr = WorkerManager({"proactive_workspace_roots": []})
    assert mgr.run_now("missing") == []


def test_get_worker_manager_singleton():
    import autonomous_workers as aw
    aw._manager = None
    a = get_worker_manager({"proactive_workspace_roots": []})
    b = get_worker_manager({"proactive_workspace_roots": ["/tmp"]})
    assert a is b
    aw._manager = None
