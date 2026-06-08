#!/usr/bin/env python3
"""Fail CI if any project .py file is not valid UTF-8."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {
    ".git", ".claude", "venv", "web", "web_dist", "web_vite_backup",
    "node_modules", "__pycache__", ".pytest_cache", "memory_data",
}

bad: list[str] = []
for path in ROOT.rglob("*.py"):
    if any(part in SKIP for part in path.parts):
        continue
    try:
        path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        bad.append(f"{path.relative_to(ROOT)}: {e}")

if bad:
    print("Non-UTF-8 Python files (use UTF-8 encoding):")
    for line in bad:
        print(f"  {line}")
    sys.exit(1)

print(f"UTF-8 OK ({sum(1 for p in ROOT.rglob('*.py') if not any(s in p.parts for s in SKIP))} files checked)")
