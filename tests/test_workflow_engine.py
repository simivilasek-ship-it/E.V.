"""Tests for E.V. WorkflowEngine."""
from __future__ import annotations
import sys
import os
import time
from unittest.mock import patch, MagicMock

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _make_engine(tmp_path=None):
    """Helper: fresh engine with tmp workflows file."""
    import workflow_engine as we
    # Reset singleton so each test gets a clean engine
    we._engine = None

    if tmp_path is not None:
        we.WORKFLOWS_FILE = tmp_path / "workflows.json"

    engine = we.WorkflowEngine()
    return engine, we


def test_add_and_list(tmp_path):
    """Přidej workflow → list vrátí 1 položku."""
    from workflow_engine import Workflow
    engine, _ = _make_engine(tmp_path)

    wf = Workflow(
        id="test01",
        name="CPU Alert",
        trigger_type="cpu_threshold",
        trigger_config={"threshold": 90},
        action="notifikace CPU přetíženo",
    )
    engine.add(wf)
    items = engine.list_all()
    assert len(items) == 1
    assert items[0]["id"] == "test01"
    assert items[0]["name"] == "CPU Alert"


def test_remove(tmp_path):
    """Přidej + odstraň → prázdné."""
    from workflow_engine import Workflow
    engine, _ = _make_engine(tmp_path)

    wf = Workflow(
        id="rem01",
        name="To Remove",
        trigger_type="manual",
        trigger_config={},
        action="nic",
    )
    engine.add(wf)
    assert len(engine.list_all()) == 1

    result = engine.remove("rem01")
    assert result is True
    assert len(engine.list_all()) == 0


def test_toggle(tmp_path):
    """enabled → disabled → enabled."""
    from workflow_engine import Workflow
    engine, _ = _make_engine(tmp_path)

    wf = Workflow(
        id="tog01",
        name="Toggle Test",
        trigger_type="manual",
        trigger_config={},
        action="nic",
        enabled=True,
    )
    engine.add(wf)

    # First toggle: True → False
    new_state = engine.toggle("tog01")
    assert new_state is False
    assert engine._workflows["tog01"].enabled is False

    # Second toggle: False → True
    new_state = engine.toggle("tog01")
    assert new_state is True
    assert engine._workflows["tog01"].enabled is True


def test_cpu_trigger_below(tmp_path):
    """CPU 50%, threshold 90 → should NOT trigger (returns False)."""
    from workflow_engine import Workflow
    engine, _ = _make_engine(tmp_path)

    wf = Workflow(
        id="cpu01",
        name="CPU High",
        trigger_type="cpu_threshold",
        trigger_config={"threshold": 90},
        action="alert",
    )

    mock_psutil = MagicMock()
    mock_psutil.cpu_percent.return_value = 50.0

    result = engine._should_trigger(wf, mock_psutil)
    assert result is False


def test_time_trigger_match(tmp_path):
    """Mock time → True pokud 'HH:MM' sedí."""
    import datetime as _dt
    from workflow_engine import Workflow
    engine, _ = _make_engine(tmp_path)

    wf = Workflow(
        id="time01",
        name="Morning Briefing",
        trigger_type="time",
        trigger_config={"time": "09:00"},
        action="přečti zprávy",
    )

    mock_psutil = MagicMock()

    # Build a fake datetime.datetime whose .now() returns 09:00
    class _FakeDT(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 6, 2, 9, 0, 0)

    fake_datetime_module = MagicMock()
    fake_datetime_module.datetime = _FakeDT

    with patch("workflow_engine.datetime", fake_datetime_module):
        result = engine._should_trigger(wf, mock_psutil)

    assert result is True
