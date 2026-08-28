"""Launcher helpers — Node.js discovery for the Next.js UI build."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.api.runner import _user_node_bin_dirs, ensure_node_on_path, ensure_voice_deps

pytestmark = [pytest.mark.unit]


def test_user_node_bin_dirs_includes_local_node(tmp_path: Path):
    local = tmp_path / ".local" / "node" / "bin"
    local.mkdir(parents=True)
    dirs = _user_node_bin_dirs(tmp_path)
    assert local in dirs


def test_ensure_node_on_path_uses_local_install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    bin_dir = tmp_path / ".local" / "node" / "bin"
    bin_dir.mkdir(parents=True)
    npm = bin_dir / "npm"
    npm.write_text("#!/bin/sh\n", encoding="utf-8")
    npm.chmod(0o755)

    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    found = ensure_node_on_path(home=tmp_path)
    assert found == npm
    assert str(bin_dir) in os.environ["PATH"].split(os.pathsep)


def test_ensure_voice_deps_is_callable():
    ensure_voice_deps()
