"""Tests for jarvis log CLI."""
import pytest

pytestmark = pytest.mark.unit


def test_log_today_text(capsys):
    from jarvis_cli import cmd_log
    assert cmd_log(["--today"]) == 0
    out = capsys.readouterr().out
    assert out.strip()


def test_log_markdown(capsys):
    from jarvis_cli import cmd_log
    assert cmd_log(["--markdown", "--today"]) == 0
    out = capsys.readouterr().out
    assert "# JARVIS" in out or "Žádná" in out or "aktivita" in out.lower()
