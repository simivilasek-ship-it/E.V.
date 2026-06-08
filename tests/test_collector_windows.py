"""Testy Windows vylepšení ActivityCollector."""

import platform
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestWindowsCollector:
    def test_git_repo_candidates_includes_windows_paths(self, monkeypatch, tmp_path):
        monkeypatch.setattr(platform, "system", lambda: "Windows")
        od = tmp_path / "OneDrive"
        od.mkdir()
        (od / "Documents").mkdir()
        monkeypatch.setenv("OneDrive", str(od))

        from activity_collector import ActivityCollector
        col = ActivityCollector()
        bases = col._git_repo_candidates()
        paths = {str(b).replace("\\", "/") for b in bases}
        assert any("OneDrive" in p for p in paths)
        assert any("Documents" in p for p in paths)

    def test_find_git_repos_skips_without_git(self, monkeypatch):
        monkeypatch.setattr("activity_collector.shutil.which", lambda _: None)
        from activity_collector import ActivityCollector
        assert ActivityCollector()._find_git_repos() == []

    def test_infer_project_cursor_title(self):
        from activity_collector import ActivityCollector
        col = ActivityCollector()
        title = "jarvis.ts - Jarvis - Cursor"
        assert col._infer_project(title) == "Jarvis"

    def test_infer_project_vscode_title(self):
        from activity_collector import ActivityCollector
        col = ActivityCollector()
        title = "README.md — my-app — Visual Studio Code"
        assert col._infer_project(title) == "my-app"

    def test_git_repo_finds_nested_repo(self, tmp_path, monkeypatch):
        repo = tmp_path / "Jarvis"
        repo.mkdir()
        (repo / ".git").mkdir()
        monkeypatch.setattr(
            "activity_collector.ActivityCollector._git_repo_candidates",
            lambda self: [tmp_path],
        )
        monkeypatch.setattr("activity_collector.shutil.which", lambda _: "git")

        from activity_collector import ActivityCollector
        found = ActivityCollector()._find_git_repos()
        assert repo in found

    @patch("activity_collector.platform.system", return_value="Windows")
    def test_get_active_window_windows_ctypes(self, _mock_sys):
        from activity_collector import ActivityCollector
        col = ActivityCollector()
        assert col._infer_project("jarvis.ts - Jarvis - Cursor") == "Jarvis"
