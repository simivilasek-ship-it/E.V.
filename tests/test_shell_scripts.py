"""Syntax checks for installer and launcher scripts."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = [pytest.mark.unit]


@pytest.mark.skipif(not shutil.which("bash"), reason="bash not available")
@pytest.mark.parametrize("script", ["install.sh", "start.sh", "start_jarvis.sh"])
def test_bash_syntax(script):
    path = ROOT / script
    if not path.is_file():
        pytest.skip(f"{script} missing")
    proc = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


def test_makefile_help_has_closed_quotes():
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    help_block = text.split("help:", 1)[1].split("\n\n", 1)[0]
    # Each @echo line in help should be a single quoted string
    echo_lines = [ln for ln in help_block.splitlines() if "@echo" in ln]
    assert echo_lines, "make help has no echo lines"
    for ln in echo_lines:
        assert ln.count('"') % 2 == 0, f"Unclosed quote in Makefile help: {ln}"


def test_systemd_unit_placeholder():
    text = (ROOT / "desktop/jarvis.service").read_text(encoding="utf-8")
    assert "@EV_DIR@" in text
    assert "@E.V._DIR@" not in text
    install = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "s|@EV_DIR@" in install
