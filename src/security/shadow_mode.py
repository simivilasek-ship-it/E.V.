"""Shadow Mode — developer assistant (MVP)

Runs lightweight repository checks and produces suggestions.
This is intentionally conservative: it does NOT modify code automatically.

Suggestions currently include:
- TODO/FIXME scan
- recent git failures hint (best-effort)

Integration points:
- Can be called via command action `shadow_suggest`
- Can be scheduled or triggered by ProactiveEngine
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ShadowSuggestion:
    kind: str
    message: str
    file: str = ""
    line: int = 0


def _iter_files(roots: List[str], exts: tuple[str, ...] = (".py", ".js", ".ts", ".jsx", ".tsx"), limit: int = 800) -> List[Path]:
    files: List[Path] = []
    for r in roots:
        rp = Path(r).expanduser()
        if not rp.exists():
            continue
        if rp.is_file():
            if rp.suffix in exts:
                files.append(rp)
            continue
        for p in rp.rglob("*"):
            if len(files) >= limit:
                break
            if p.is_file() and p.suffix in exts and ".venv" not in str(p) and "node_modules" not in str(p):
                files.append(p)
        if len(files) >= limit:
            break
    return files


def scan_todos(roots: List[str], limit_hits: int = 60) -> List[ShadowSuggestion]:
    suggestions: List[ShadowSuggestion] = []
    todo_re = re.compile(r"\b(TODO|FIXME|XXX)\b")

    for f in _iter_files(roots):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
            for i, line in enumerate(text.splitlines(), 1):
                if todo_re.search(line):
                    suggestions.append(
                        ShadowSuggestion(
                            kind="todo",
                            message=line.strip()[:160],
                            file=str(f),
                            line=i,
                        )
                    )
                    if len(suggestions) >= limit_hits:
                        return suggestions
        except Exception:
            continue
    return suggestions


def git_recent_commits(repo_dir: str, n: int = 10) -> str:
    try:
        out = subprocess.check_output(["git", "-C", repo_dir, "log", "--oneline", "-n", str(n)], stderr=subprocess.DEVNULL, text=True)
        return out.strip()
    except Exception:
        return ""


def build_report(roots: List[str]) -> str:
    lines: List[str] = []
    lines.append("# Shadow Mode suggestions\n")

    todos = scan_todos(roots)
    if todos:
        lines.append("## TODO / FIXME\n")
        for s in todos[:20]:
            loc = f"{s.file}:{s.line}" if s.file else ""
            lines.append(f"- {loc} {s.message}")
    else:
        lines.append("## TODO / FIXME\n- (žádné nenalezeny v limitu)\n")

    # git summary (best effort)
    for r in roots:
        rp = Path(r).expanduser()
        if rp.is_dir() and (rp / ".git").exists():
            commits = git_recent_commits(str(rp), 8)
            if commits:
                lines.append("\n## Recent git commits\n")
                lines.append("```\n" + commits + "\n```")
            break

    return "\n".join(lines).strip() + "\n"


def cmd_shadow_suggest(config: dict) -> str:
    if not bool(config.get("shadow_mode_enabled", False)):
        return "Shadow mode je vypnutý (shadow_mode_enabled=false)."
    roots = config.get("shadow_mode_workspace_roots") or config.get("proactive_workspace_roots") or [os.getcwd()]
    return build_report(list(roots))
