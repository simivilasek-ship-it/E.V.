"""Tests for project_profiles module."""
import pytest
import tempfile
import subprocess
from pathlib import Path

pytestmark = pytest.mark.unit


def test_detect_returns_dict():
    from project_profiles import detect_project
    result = detect_project()
    assert isinstance(result, dict)
    assert "name" in result
    assert "languages" in result
    assert "suggested_tools" in result


def test_detect_python_markers(tmp_path):
    from project_profiles import detect_project
    (tmp_path / "requirements.txt").write_text("requests\n")
    result = detect_project(str(tmp_path))
    assert "python" in result["languages"]


def test_detect_typescript_markers(tmp_path):
    from project_profiles import detect_project
    (tmp_path / "tsconfig.json").write_text("{}")
    result = detect_project(str(tmp_path))
    assert "typescript" in result["languages"]


def test_git_root_found():
    from project_profiles import _find_git_root
    # The project itself is a git repo
    root = _find_git_root(Path("."))
    assert root is not None


def test_description_not_empty():
    from project_profiles import detect_project
    result = detect_project()
    # Should at minimum have the project name
    assert result["description"]


def test_get_project_profile_cached():
    from project_profiles import get_project_profile
    p1 = get_project_profile()
    p2 = get_project_profile()
    assert p1["name"] == p2["name"]
