"""
Proactive Engine — context-aware triggers and daily summaries
- Polls ContextOrchestrator for active window changes
- When a .py file in VS Code is detected, scans for TODO/FIXME, recent failures and git commits
- Sends gentle notifications via NotificationEngine
- Generates daily markdown reports at configured time
"""
from __future__ import annotations
import threading
import time
import os
import subprocess
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

from event_bus import get_event_bus, EventType
from context_orchestrator import get_context_orchestrator
from notification_engine import get_notification_engine
from scheduler import get_scheduler
from config import CONFIG

logger = logging.getLogger(__name__)


class ProactiveEngine:
    def __init__(self, config: dict = None, bus=None, scheduler=None, notif=None, start: bool = True):
        self.config = config or CONFIG
        self.bus = bus or get_event_bus()
        self.scheduler = scheduler or get_scheduler()
        self.notif = notif or get_notification_engine(self.config)
        self._orch = get_context_orchestrator(self.config)
        self._last_active: str = ""
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._poll_interval = float(self.config.get("proactive_poll_interval", 2.0))
        # schedule daily report at configured time (default 18:00)
        t = str(self.config.get("proactive_daily_time", "18:00"))
        try:
            hour, minute = (int(p) for p in t.split(":"))
        except Exception:
            hour, minute = 18, 0
        # schedule daily report
        try:
            self.scheduler.every_day_at(hour, minute, self.generate_daily_report, name="proactive_daily_report")
        except Exception as e:
            logger.debug(f"ProactiveEngine schedule fail: {e}")

        if start:
            self.start()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="ProactiveEngine")
        self._thread.start()
        logger.info("ProactiveEngine started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def _loop(self):
        while self._running:
            try:
                # get active window name
                try:
                    active = self._orch._get_active_window()
                except Exception:
                    active = ""

                if active and active != self._last_active:
                    self._last_active = active
                    try:
                        self._handle_active_change(active)
                    except Exception as e:
                        logger.debug(f"Proactive handle error: {e}")
            except Exception as e:
                logger.debug(f"Proactive loop error: {e}")
            time.sleep(self._poll_interval)

    def _handle_active_change(self, active_title: str) -> None:
        """Called when active window title changes."""
        logger.debug(f"Proactive active window changed: {active_title}")
        # detect VS Code + python file by simple heuristics
        lower = active_title.lower()
        if ".py" in lower and ("visual studio code" in lower or "vscode" in lower or "code" in lower):
            # try extract filename
            import re
            m = re.search(r"([\w\-\. ]+\.py)", active_title)
            filename = m.group(1).strip() if m else None
            file_path = None
            if filename:
                file_path = self._locate_file(filename)
            if file_path:
                todos = self._scan_todos(file_path)
                failures = self._get_recent_failures()
                git_summary = self._get_git_summary(file_path)
                if todos or failures:
                    msg = self._build_suggestion_message(todos, failures, git_summary)
                    try:
                        self.notif.send("Chceš pokračovat na tomhle tasku?", msg)
                    except Exception:
                        logger.debug("Notification send failed")

    def _locate_file(self, filename: str) -> Optional[str]:
        """Search workspace roots for filename (fast heuristic with limits)."""
        roots: List[str] = self.config.get("proactive_workspace_roots", []) or [os.getcwd(), str(Path.home())]
        max_files = int(self.config.get("proactive_max_files_scan", 2000))
        start_ts = time.time()
        for root in roots:
            try:
                rootp = Path(root)
                if not rootp.exists():
                    continue
                scanned = 0
                for dirpath, dirnames, filenames in os.walk(root):
                    if filename in filenames:
                        return str(Path(dirpath) / filename)
                    scanned += len(filenames)
                    if scanned > max_files:
                        break
                    # time limit
                    if time.time() - start_ts > 1.0:
                        break
            except Exception:
                continue
        return None

    def _scan_todos(self, file_path: str) -> List[dict]:
        todos = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    if "TODO" in line or "FIXME" in line:
                        todos.append({"line": i, "text": line.strip()})
        except Exception as e:
            logger.debug(f"todo scan failed: {e}")
        return todos

    def _get_recent_failures(self) -> List[str]:
        recent = []
        try:
            history = self.bus.get_history(limit=200)
            cutoff = time.time() - 24 * 3600
            for e in reversed(history):
                if e.timestamp < cutoff:
                    break
                if e.type in (EventType.CMD_ERROR, EventType.LLM_ERROR):
                    txt = str(e.data or "")
                    if "pytest" in txt or "test" in txt.lower():
                        recent.append(txt)
            return recent
        except Exception:
            return []

    def _get_git_summary(self, file_path: str) -> str:
        try:
            p = Path(file_path)
            repo = p.parent
            while repo != repo.parent:
                if (repo / ".git").exists():
                    break
                repo = repo.parent
            if not (repo / ".git").exists():
                return ""
            out = subprocess.check_output(["git", "-C", str(repo), "log", "--since=7.days", "--oneline", "-n", "5"], stderr=subprocess.DEVNULL, text=True)
            return out.strip()
        except Exception:
            return ""

    def _build_suggestion_message(self, todos, failures, git_summary) -> str:
        parts = []
        if todos:
            parts.append(f"Máš {len(todos)} TODO v aktuálním souboru, např.: {todos[0]['text']}")
        if failures:
            parts.append("Nedávné failing tests: " + (failures[0] if failures else ""))
        if git_summary:
            first = git_summary.splitlines()[0] if git_summary else ""
            parts.append(f"Poslední commit: {first}")
        return " · ".join(parts)

    def generate_daily_report(self):
        """Generate a simple markdown daily report saved to ~/jarvis_reports/YYYY-MM-DD.md"""
        try:
            repo_roots = self.config.get("proactive_workspace_roots", []) or [os.getcwd(), str(Path.home())]
            date = datetime.now().strftime("%Y-%m-%d")
            outdir = Path.home() / "jarvis_reports"
            outdir.mkdir(parents=True, exist_ok=True)
            path = outdir / f"{date}.md"
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# Jarvis Daily Summary — {date}\n\n")
                f.write("## Commits (last 24h)\n")
                for root in repo_roots:
                    try:
                        if not Path(root).exists():
                            continue
                        out = subprocess.check_output(["git", "-C", str(root), "log", "--since=24.hours", "--oneline", "-n", "20"], stderr=subprocess.DEVNULL, text=True)
                        if out.strip():
                            f.write(f"### {root}\n```
{out.strip()}
```")
                    except Exception:
                        continue
                f.write("\n## Recent Events\n")
                history = self.bus.get_history(limit=200)
                for e in reversed(history):
                    ts = datetime.fromtimestamp(e.timestamp).strftime("%H:%M:%S")
                    f.write(f"- [{ts}] {e.type}: {e.data}\n")
            # notify user
            try:
                self.notif.send("Jarvis: Denní shrnutí hotovo", f"Uložen do {path}")
            except Exception:
                pass
            logger.info(f"Daily report generated: {path}")
            return str(path)
        except Exception as e:
            logger.debug(f"Daily report failed: {e}")
            return ""
