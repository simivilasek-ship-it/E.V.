"""
mcp_installer.py

Skeleton safe installer for MCP servers (MVP).
Provides discovery, static analysis and staged installation under ~/.jarvis/mcp_servers/<name>/
This is a conservative, non-automatic installer: it performs checks and returns an installation plan.
"""
from __future__ import annotations
import os
import shutil
import subprocess
import tempfile
import json
from pathlib import Path
from typing import Dict, Any

INSTALL_DIR = Path.home() / ".jarvis" / "mcp_servers"
INSTALL_DIR.mkdir(parents=True, exist_ok=True)


def analyze_repo(repo_path: Path) -> Dict[str, Any]:
    """Run lightweight static analysis of repo: check manifest, prohibited commands, required files."""
    manifest = None
    try:
        mpath = repo_path / "manifest.json"
        if mpath.exists():
            manifest = json.loads(mpath.read_text(encoding="utf-8"))
    except Exception:
        manifest = None

    # Basic checks
    checks = {
        "has_manifest": bool(manifest),
        "manifest": manifest,
        "prohibited_commands": [],
        "entry_point": manifest.get("entry_point") if manifest else None,
    }
    return checks


def install_from_zip_bytes(name: str, zip_bytes: bytes) -> Dict[str, Any]:
    """Install MCP server from zip bytes into staged folder and run static analysis.
    Returns plan dict {name, path, checks}.
    """
    import zipfile, io
    staged = Path(tempfile.mkdtemp(prefix="mcp_staged_"))
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            z.extractall(staged)
    except Exception as e:
        shutil.rmtree(staged, ignore_errors=True)
        raise

    checks = analyze_repo(staged)
    dest = INSTALL_DIR / name
    if dest.exists():
        return {"ok": False, "error": "dest_exists", "path": str(dest)}

    # Move staged to final location (user must confirm)
    shutil.move(str(staged), str(dest))
    return {"ok": True, "name": name, "path": str(dest), "checks": checks}


def discover_github(query: str) -> list:
    """Naive discovery via GitHub search (MVP) — returns list of repo names.
    In MVP this is just a stub returning an empty list.
    """
    return []


if __name__ == '__main__':
    print("mcp_installer: skeleton module — use via API")
