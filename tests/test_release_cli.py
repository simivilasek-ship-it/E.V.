"""Tests for jarvis release CLI (single-source versioning)."""
import pytest
import re
from pathlib import Path
from unittest.mock import patch

pytestmark = pytest.mark.unit


def test_release_dry_run_leaves_files_unchanged(tmp_path):
    """Dry run should NOT modify any files."""
    config = tmp_path / "config.py"
    config.write_text('__version__ = "5.12.0"\n', encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text("# CHANGELOG\n\nold\n", encoding="utf-8")

    import jarvis_cli
    with patch.object(jarvis_cli, "__file__", str(tmp_path / "jarvis_cli.py")):
        ret = jarvis_cli.cmd_release(["--dry-run", "--bump", "patch"])

    assert ret == 0
    assert config.read_text() == '__version__ = "5.12.0"\n'


def test_release_bumps_config_version(tmp_path):
    """Release (no dry-run) should bump version in config.py."""
    config = tmp_path / "config.py"
    config.write_text('__version__ = "5.12.0"\n', encoding="utf-8")
    cl = tmp_path / "CHANGELOG.md"
    cl.write_text("# CHANGELOG\n\n", encoding="utf-8")

    import jarvis_cli
    with patch.object(jarvis_cli, "__file__", str(tmp_path / "jarvis_cli.py")):
        ret = jarvis_cli.cmd_release(["--bump", "patch"])

    assert ret == 0
    content = config.read_text()
    assert '5.12.1' in content


def test_release_minor_bump(tmp_path):
    config = tmp_path / "config.py"
    config.write_text('__version__ = "5.12.0"\n', encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text("# CHANGELOG\n\n", encoding="utf-8")

    import jarvis_cli
    with patch.object(jarvis_cli, "__file__", str(tmp_path / "jarvis_cli.py")):
        jarvis_cli.cmd_release(["--bump", "minor"])

    assert '5.13.0' in config.read_text()


def test_release_major_bump(tmp_path):
    config = tmp_path / "config.py"
    config.write_text('__version__ = "5.12.0"\n', encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text("# CHANGELOG\n\n", encoding="utf-8")

    import jarvis_cli
    with patch.object(jarvis_cli, "__file__", str(tmp_path / "jarvis_cli.py")):
        jarvis_cli.cmd_release(["--bump", "major"])

    content = config.read_text()
    assert '6.0.0' in content


def test_release_changelog_updated(tmp_path):
    """Release should prepend entry to CHANGELOG.md."""
    (tmp_path / "config.py").write_text('__version__ = "5.12.0"\n', encoding="utf-8")
    cl = tmp_path / "CHANGELOG.md"
    cl.write_text("# CHANGELOG\n\nexisting\n", encoding="utf-8")

    import jarvis_cli
    with patch.object(jarvis_cli, "__file__", str(tmp_path / "jarvis_cli.py")):
        jarvis_cli.cmd_release(["--bump", "patch"])

    changelog = cl.read_text()
    assert "5.12.1" in changelog
    assert "existing" in changelog  # original content preserved


def test_release_missing_version_returns_error(tmp_path):
    """Should return error code 1 if config.py has no __version__."""
    (tmp_path / "config.py").write_text("# no version here\n", encoding="utf-8")

    import jarvis_cli
    with patch.object(jarvis_cli, "__file__", str(tmp_path / "jarvis_cli.py")):
        ret = jarvis_cli.cmd_release(["--dry-run"])

    assert ret == 1
