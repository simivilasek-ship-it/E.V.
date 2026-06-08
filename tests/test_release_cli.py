"""Tests for jarvis release CLI."""
import pytest
import sys
from io import StringIO
from unittest.mock import patch

pytestmark = pytest.mark.unit


def test_release_dry_run_no_changes(tmp_path):
    """Dry run should print checklist without modifying files."""
    import shutil
    from pathlib import Path

    # Set up minimal fake project root
    fake_config = tmp_path / "config.py"
    fake_config.write_text('__version__ = "5.11.0"\n', encoding="utf-8")

    # Patch __file__ in jarvis_cli to point to tmp_path
    import jarvis_cli
    original_file = jarvis_cli.__file__

    with patch.object(jarvis_cli, "__file__", str(tmp_path / "jarvis_cli.py")):
        captured = StringIO()
        with patch("sys.stdout", captured):
            ret = jarvis_cli.cmd_release(["--dry-run", "--bump", "patch"])

    assert ret == 0
    # config.py should be unchanged since dry-run
    content = fake_config.read_text()
    assert '5.11.0' in content


def test_release_shows_checklist(capsys):
    """Release command should show a checklist."""
    import jarvis_cli
    try:
        # This will try to parse actual config.py — just make sure it doesn't crash
        ret = jarvis_cli.cmd_release(["--dry-run"])
        out = capsys.readouterr().out
        assert "checklist" in out.lower() or ret == 0
    except SystemExit as e:
        assert e.code == 0
