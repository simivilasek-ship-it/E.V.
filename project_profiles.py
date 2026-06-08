"""
JARVIS Project Profiles
Auto-detects current git repository and returns project-specific context.
"""
from __future__ import annotations

import os
import subprocess
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_LANG_MARKERS = {
    "python":     ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"],
    "javascript": ["package.json"],
    "typescript": ["tsconfig.json"],
    "rust":       ["Cargo.toml"],
    "go":         ["go.mod"],
    "java":       ["pom.xml", "build.gradle"],
    "cpp":        ["CMakeLists.txt", "Makefile"],
    "docker":     ["Dockerfile", "docker-compose.yml"],
}

_TOOL_HINTS = {
    "python":     ["read_file", "web_search", "memory_recall", "git_status"],
    "javascript": ["read_file", "web_search", "fetch_url"],
    "typescript": ["read_file", "web_search", "fetch_url"],
    "rust":       ["read_file", "web_search"],
    "go":         ["read_file", "web_search"],
    "docker":     ["read_file", "web_search"],
}


def detect_project(cwd: Optional[str] = None) -> dict[str, Any]:
    """Detect current project from cwd or active git repo."""
    path = Path(cwd) if cwd else Path.cwd()

    result = {
        "name": path.name,
        "path": str(path),
        "languages": [],
        "suggested_tools": [],
        "git_branch": "",
        "git_remote": "",
        "has_tests": False,
        "has_docker": False,
        "description": "",
    }

    # Walk up to find git root
    git_root = _find_git_root(path)
    if git_root:
        result["path"] = str(git_root)
        result["name"] = git_root.name
        result["git_branch"] = _git_branch(git_root)
        result["git_remote"] = _git_remote(git_root)
    else:
        git_root = path

    # Detect languages
    langs: list[str] = []
    for lang, markers in _LANG_MARKERS.items():
        if any((git_root / m).exists() for m in markers):
            langs.append(lang)
    result["languages"] = langs

    # Detect tests
    result["has_tests"] = any([
        (git_root / "tests").is_dir(),
        (git_root / "test").is_dir(),
        bool(list(git_root.glob("test_*.py"))),
    ])

    result["has_docker"] = (git_root / "Dockerfile").exists() or (git_root / "docker-compose.yml").exists()

    # Suggested tools (union of all detected langs)
    tools: set[str] = set()
    for lang in langs:
        tools.update(_TOOL_HINTS.get(lang, []))
    result["suggested_tools"] = list(tools)

    # Human-readable description
    lang_str = " + ".join(langs[:3]) if langs else "unknown"
    parts = [f"Project: {result['name']} ({lang_str})"]
    if result["git_branch"]:
        parts.append(f"Branch: {result['git_branch']}")
    if result["has_tests"]:
        parts.append("has tests")
    if result["has_docker"]:
        parts.append("Docker")
    result["description"] = " · ".join(parts)

    return result


def _find_git_root(start: Path) -> Optional[Path]:
    current = start.resolve()
    for _ in range(10):
        if (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _git_branch(root: Path) -> str:
    try:
        r = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=root, capture_output=True, text=True, timeout=3
        )
        return r.stdout.strip()
    except Exception:
        return ""


def _git_remote(root: Path) -> str:
    try:
        r = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=root, capture_output=True, text=True, timeout=3
        )
        url = r.stdout.strip()
        # Strip tokens from URL
        if "@" in url:
            url = url.split("@", 1)[-1]
        return url
    except Exception:
        return ""


_cache: dict[str, Any] = {}
_cache_cwd: str = ""


def get_project_profile(cwd: Optional[str] = None) -> dict[str, Any]:
    """Cached project profile (invalidated on cwd change)."""
    global _cache, _cache_cwd
    key = cwd or str(Path.cwd())
    if key != _cache_cwd or not _cache:
        _cache = detect_project(cwd)
        _cache_cwd = key
    return _cache
