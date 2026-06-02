import os
import tempfile
import shutil
from pathlib import Path
import pytest

from proactive import ProactiveEngine

pytestmark = [pytest.mark.unit]


def test_locate_and_scan_todos(tmp_path):
    # create workspace and file
    file = tmp_path / "example.py"
    file.write_text("# TODO: implement\nprint('hello')\n# FIXME: bug")

    cfg = {"proactive_workspace_roots": [str(tmp_path)]}
    eng = ProactiveEngine(config=cfg, start=False)

    found = eng._locate_file("example.py")
    assert found is not None
    todos = eng._scan_todos(found)
    assert len(todos) == 2
    assert "TODO" in todos[0]["text"] or "FIXME" in todos[0]["text"]


def test_generate_daily_report_creates_file(tmp_path):
    cfg = {"proactive_workspace_roots": [str(tmp_path)]}
    eng = ProactiveEngine(config=cfg, start=False)
    path = eng.generate_daily_report()
    assert path != ""
    assert Path(path).exists()
    # cleanup
    Path(path).unlink()


def test_handle_active_change_notifies(tmp_path, monkeypatch):
    # create file with TODO
    file = tmp_path / "task.py"
    file.write_text("# TODO: finish this\nprint(1)")

    cfg = {"proactive_workspace_roots": [str(tmp_path)]}
    eng = ProactiveEngine(config=cfg, start=False)

    # ensure security manager allows operations during test
    class DummySM:
        def check(self, action, params=None, user_text=""):
            return True, "ok"
    try:
        import security_v2
        monkeypatch.setattr(security_v2, 'get_security_manager', lambda: DummySM())
    except Exception:
        pass

    sent = {}

    class DummyNotif:
        def send(self, title, body, urgent=False):
            sent['title'] = title
            sent['body'] = body
            return True

    eng.notif = DummyNotif()

    # simulate active window title
    title = "task.py — Visual Studio Code"
    eng._handle_active_change(title)

    assert 'title' in sent
    assert 'Chceš' in sent['title'] or 'Pokračovat' in sent['title'] or sent['body']
