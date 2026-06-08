"""
JARVIS — Activity Collector
Sleduje aplikace, git, docker a zapisuje do ActivityStore.
"""

from __future__ import annotations

import logging
import os
import platform
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

import psutil

from activity_store import get_activity_store

logger = logging.getLogger(__name__)

# Aplikace k sledování (název procesu → zobrazovaný název)
WATCHED_APPS = {
    "code": "VS Code",
    "code.exe": "VS Code",
    "cursor": "Cursor",
    "cursor.exe": "Cursor",
    "chrome": "Chrome",
    "chrome.exe": "Chrome",
    "firefox": "Firefox",
    "firefox.exe": "Firefox",
    "docker": "Docker",
    "docker.exe": "Docker Desktop",
    "com.docker.backend": "Docker",
    "node": "Node.js",
    "node.exe": "Node.js",
    "python": "Python",
    "python.exe": "Python",
    "pwsh": "PowerShell",
    "powershell": "PowerShell",
    "powershell.exe": "PowerShell",
    "cmd": "CMD",
    "cmd.exe": "CMD",
    "wt": "Windows Terminal",
    "WindowsTerminal": "Windows Terminal",
}

GIT_KEYWORDS = ("commit", "push", "pull", "merge", "release", "fix", "bug")


class ActivityCollector:
    """Background kolektor pracovní aktivity."""

    def __init__(self, interval: float = 20.0):
        self._interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._store = get_activity_store()
        self._last_window = ""
        self._last_apps: Set[str] = set()
        self._window_since: float = time.time()
        self._git_heads: Dict[str, str] = {}
        self._docker_containers: Dict[str, dict] = {}
        self._build_fail_counts: Dict[str, int] = {}

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="ActivityCollector")
        self._thread.start()
        self._store.record(
            "session.summary", title="JARVIS session start",
            source="activity_collector",
        )
        logger.info("ActivityCollector spuštěn")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)

    def _loop(self):
        while self._running:
            try:
                self._tick_apps()
                self._tick_git()
                self._tick_docker()
            except Exception as e:
                logger.debug(f"ActivityCollector tick: {e}")
            time.sleep(self._interval)

    # ── Aplikace / okna ───────────────────────────────

    def _get_active_window(self) -> str:
        system = platform.system()
        try:
            if system == "Windows":
                import ctypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd) + 1
                buf = ctypes.create_unicode_buffer(length)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length)
                return buf.value[:120]
            elif system == "Linux":
                r = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowname"],
                    capture_output=True, text=True, timeout=1,
                )
                if r.returncode == 0:
                    return r.stdout.strip()[:120]
            elif system == "Darwin":
                r = subprocess.run(
                    ["osascript", "-e",
                     'tell application "System Events" to get name of first process whose frontmost is true'],
                    capture_output=True, text=True, timeout=2,
                )
                if r.returncode == 0:
                    return r.stdout.strip()[:120]
        except Exception:
            pass
        return ""

    def _detect_running_apps(self) -> Set[str]:
        found: Set[str] = set()
        for proc in psutil.process_iter(["name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                for key, label in WATCHED_APPS.items():
                    if key.lower() in name:
                        found.add(label)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return found

    def _infer_project(self, window: str) -> str:
        """Odhad projektu z titulku okna."""
        for part in re.split(r"[\-—|/\\]", window):
            part = part.strip()
            if part and len(part) > 2 and part not in (
                "Visual Studio Code", "Cursor", "Chrome", "Google Chrome",
                "Mozilla Firefox", "Docker Desktop",
            ):
                # VS Code: "file.py - project - Visual Studio Code"
                if "Visual Studio Code" in window or "Cursor" in window:
                    return part
        # Git repo z cwd
        try:
            cwd = Path.cwd()
            if (cwd / ".git").exists():
                return cwd.name
        except Exception:
            pass
        return ""

    def _tick_apps(self):
        window = self._get_active_window()
        running = self._detect_running_apps()
        now = time.time()

        # Nově spuštěné aplikace
        for app in running - self._last_apps:
            self._store.record(
                "app.open", title=app, source="activity_collector",
                project=self._infer_project(window),
            )
        self._last_apps = running

        # Změna aktivního okna
        if window and window != self._last_window:
            duration_ms = int((now - self._window_since) * 1000) if self._last_window else 0
            if self._last_window and duration_ms > 5000:
                self._store.record(
                    "app.focus", title=self._last_window,
                    source="activity_collector",
                    project=self._infer_project(self._last_window),
                    duration_ms=duration_ms,
                )
            self._last_window = window
            self._window_since = now

    # ── Git ───────────────────────────────────────────

    def _find_git_repos(self) -> List[Path]:
        repos: List[Path] = []
        candidates = [
            Path.cwd(),
            Path.home() / "Projects",
            Path.home() / "Developer",
            Path.home() / "repos",
            Path(__file__).parent,
        ]
        seen: Set[str] = set()
        for base in candidates:
            if not base.exists():
                continue
            if (base / ".git").exists():
                key = str(base.resolve())
                if key not in seen:
                    seen.add(key)
                    repos.append(base)
            try:
                for child in base.iterdir():
                    if child.is_dir() and (child / ".git").exists():
                        key = str(child.resolve())
                        if key not in seen:
                            seen.add(key)
                            repos.append(child)
            except PermissionError:
                pass
        return repos[:20]

    def _git_log(self, repo: Path, n: int = 3) -> List[dict]:
        try:
            r = subprocess.run(
                ["git", "-C", str(repo), "log", f"-{n}",
                 "--format=%H|%s|%ct"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode != 0:
                return []
            commits = []
            for line in r.stdout.strip().splitlines():
                parts = line.split("|", 2)
                if len(parts) == 3:
                    commits.append({
                        "hash": parts[0][:8],
                        "msg": parts[1],
                        "ts": float(parts[2]),
                    })
            return commits
        except Exception:
            return []

    def _tick_git(self):
        for repo in self._find_git_repos():
            key = str(repo)
            commits = self._git_log(repo, n=1)
            if not commits:
                continue
            head = commits[0]["hash"]
            prev = self._git_heads.get(key)
            if prev and prev != head:
                msg = commits[0]["msg"]
                self._store.record(
                    "git.commit", title=msg[:80], detail=commits[0]["hash"],
                    source="git", project=repo.name, meta={"repo": str(repo)},
                    ts=commits[0]["ts"],
                )
                if any(k in msg.lower() for k in GIT_KEYWORDS):
                    if "fix" in msg.lower() or "bug" in msg.lower():
                        self._store.record(
                            "command.done", title=f"Bug fix: {msg[:60]}",
                            source="git", project=repo.name,
                        )
                if "release" in msg.lower():
                    self._store.record(
                        "release.create", title=msg[:80],
                        source="git", project=repo.name,
                    )
            self._git_heads[key] = head

    # ── Docker ────────────────────────────────────────

    def _tick_docker(self):
        try:
            r = subprocess.run(
                ["docker", "ps", "-a", "--format",
                 "{{.ID}}|{{.Names}}|{{.Status}}|{{.Image}}"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode != 0:
                return
            current: Dict[str, dict] = {}
            for line in r.stdout.strip().splitlines():
                parts = line.split("|", 3)
                if len(parts) < 3:
                    continue
                cid, name, status, image = parts[0], parts[1], parts[2], parts[3] if len(parts) > 3 else ""
                current[cid] = {"name": name, "status": status, "image": image}

                prev = self._docker_containers.get(cid)
                if prev is None:
                    self._store.record(
                        "docker.start", title=name, detail=image,
                        source="docker", meta={"status": status},
                    )
                elif prev["status"] != status:
                    if "Exited" in status or "Dead" in status:
                        self._store.record(
                            "docker.stop", title=name, detail=status,
                            source="docker",
                        )
                    elif "Up" in status:
                        self._store.record(
                            "docker.start", title=name, detail=status,
                            source="docker",
                        )

                # RAM spotřeba kontejneru
                try:
                    stats = subprocess.run(
                        ["docker", "stats", "--no-stream", "--format",
                         "{{.Name}}|{{.MemUsage}}|{{.CPUPerc}}"],
                        capture_output=True, text=True, timeout=5,
                    )
                    if stats.returncode == 0:
                        for sline in stats.stdout.strip().splitlines():
                            sp = sline.split("|", 2)
                            if len(sp) >= 2 and sp[0] == name:
                                mem = sp[1]
                                if "GiB" in mem:
                                    gb = float(re.search(r"([\d.]+)\s*GiB", mem).group(1)) if re.search(r"([\d.]+)\s*GiB", mem) else 0
                                    if gb > 4:
                                        self._store.record(
                                            "proactive.alert",
                                            title=f"Docker {name} používá {mem}",
                                            detail=f"Container {name} spotřebovává {mem} RAM",
                                            source="docker",
                                            meta={"action": "restart_container", "container": name},
                                        )
                except Exception:
                    pass

            for cid, info in self._docker_containers.items():
                if cid not in current:
                    self._store.record(
                        "docker.stop", title=info["name"],
                        detail="removed", source="docker",
                    )
            self._docker_containers = current
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.debug(f"Docker tick: {e}")

    def record_command(self, text: str, result: str = "", error: bool = False):
        """Zaznamená uživatelský příkaz (voláno z dashboard bridge)."""
        project = self._infer_project(self._last_window)
        etype = "command.error" if error else "command.done"
        self._store.record(
            etype if result else "command.run",
            title=text[:100], detail=(result or "")[:300],
            source="user", project=project,
        )
        # Detekce build fail
        combined = (text + " " + result).lower()
        if any(w in combined for w in ("build fail", "error:", "failed", "selhal")):
            key = project or "default"
            self._build_fail_counts[key] = self._build_fail_counts.get(key, 0) + 1
            self._store.record(
                "build.fail", title=f"Build selhal ({self._build_fail_counts[key]}x)",
                detail=result[:200] or text[:200],
                source="terminal", project=project,
                meta={"count": self._build_fail_counts[key]},
            )

    def record_agent_step(self, step_type: str, message: str, detail: str = ""):
        self._store.record(
            "agent.step", title=message[:100], detail=detail[:300],
            source="agent", meta={"step_type": step_type},
        )


_collector: Optional[ActivityCollector] = None


def get_activity_collector() -> ActivityCollector:
    global _collector
    if _collector is None:
        _collector = ActivityCollector()
    return _collector
