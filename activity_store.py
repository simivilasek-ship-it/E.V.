"""
E.V. — Work Activity Store
Append-only SQLite log pracovní aktivity: git, docker, aplikace, agenti, příkazy.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
import uuid
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Typy událostí
EVENT_TYPES = {
    "app.open", "app.focus", "app.close",
    "git.commit", "git.push", "git.pull", "git.branch",
    "docker.build", "docker.start", "docker.stop", "docker.error",
    "build.fail", "build.success",
    "command.run", "command.done", "command.error",
    "agent.step", "agent.run_start", "agent.run_end",
    "llm.query", "llm.response",
    "proactive.alert", "proactive.suggestion",
    "mission.update", "mission.complete",
    "workspace.context", "session.summary",
    "install.app", "release.create",
}


class ActivityStore:
    """Persistentní úložiště pracovní aktivity."""

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS activity_events (
        id          TEXT PRIMARY KEY,
        ts          REAL NOT NULL,
        type        TEXT NOT NULL,
        source      TEXT NOT NULL DEFAULT '',
        project     TEXT NOT NULL DEFAULT '',
        title       TEXT NOT NULL DEFAULT '',
        detail      TEXT NOT NULL DEFAULT '',
        meta        TEXT NOT NULL DEFAULT '{}',
        duration_ms INTEGER NOT NULL DEFAULT 0
    );
    CREATE INDEX IF NOT EXISTS idx_act_ts ON activity_events(ts);
    CREATE INDEX IF NOT EXISTS idx_act_type ON activity_events(type);
    CREATE INDEX IF NOT EXISTS idx_act_project ON activity_events(project);
    CREATE INDEX IF NOT EXISTS idx_act_date ON activity_events(ts);
    """

    def __init__(self, db_path: Optional[Path] = None):
        base = Path.home() / ".jarvis"
        base.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path or (base / "activity.db")
        self._lock = threading.RLock()
        with self._connect() as con:
            con.executescript(self._SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self._db_path, check_same_thread=False)
        con.row_factory = sqlite3.Row
        return con

    def record(
        self,
        event_type: str,
        title: str = "",
        detail: str = "",
        source: str = "",
        project: str = "",
        meta: Optional[dict] = None,
        duration_ms: int = 0,
        ts: Optional[float] = None,
    ) -> str:
        eid = str(uuid.uuid4())[:12]
        now = ts or time.time()
        with self._lock, self._connect() as con:
            con.execute(
                "INSERT INTO activity_events VALUES (?,?,?,?,?,?,?,?,?)",
                (eid, now, event_type, source, project, title, detail,
                 json.dumps(meta or {}, ensure_ascii=False), duration_ms),
            )
        return eid

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "ts": row["ts"],
            "type": row["type"],
            "source": row["source"],
            "project": row["project"],
            "title": row["title"],
            "detail": row["detail"],
            "meta": json.loads(row["meta"] or "{}"),
            "duration_ms": row["duration_ms"],
            "time": datetime.fromtimestamp(row["ts"]).strftime("%H:%M"),
        }

    def get_events(
        self,
        since_ts: Optional[float] = None,
        until_ts: Optional[float] = None,
        event_type: Optional[str] = None,
        project: Optional[str] = None,
        limit: int = 100,
    ) -> List[dict]:
        clauses, params = [], []
        if since_ts:
            clauses.append("ts >= ?")
            params.append(since_ts)
        if until_ts:
            clauses.append("ts <= ?")
            params.append(until_ts)
        if event_type:
            clauses.append("type = ?")
            params.append(event_type)
        if project:
            clauses.append("project = ?")
            params.append(project)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        with self._lock, self._connect() as con:
            rows = con.execute(
                f"SELECT * FROM activity_events {where} ORDER BY ts DESC LIMIT ?",
                params,
            ).fetchall()
        return [self._row_to_dict(r) for r in reversed(rows)]

    def get_today(self, limit: int = 200) -> List[dict]:
        start = datetime.combine(date.today(), datetime.min.time()).timestamp()
        return self.get_events(since_ts=start, limit=limit)

    def get_feed(self, limit: int = 50) -> List[dict]:
        return self.get_events(limit=limit)

    def count_by_type(self, since_ts: float) -> Dict[str, int]:
        with self._lock, self._connect() as con:
            rows = con.execute(
                "SELECT type, COUNT(*) as cnt FROM activity_events "
                "WHERE ts >= ? GROUP BY type",
                (since_ts,),
            ).fetchall()
        return {r["type"]: r["cnt"] for r in rows}

    def get_projects(self, since_ts: float) -> List[str]:
        with self._lock, self._connect() as con:
            rows = con.execute(
                "SELECT DISTINCT project FROM activity_events "
                "WHERE ts >= ? AND project != '' ORDER BY project",
                (since_ts,),
            ).fetchall()
        return [r["project"] for r in rows]

    def estimate_project_time(self, project: str, since_ts: float) -> float:
        """Odhad hodin strávených na projektu (z app.focus eventů)."""
        with self._lock, self._connect() as con:
            rows = con.execute(
                "SELECT duration_ms FROM activity_events "
                "WHERE ts >= ? AND project = ? AND type = 'app.focus'",
                (since_ts, project),
            ).fetchall()
        total_ms = sum(r["duration_ms"] for r in rows)
        return round(total_ms / 3_600_000, 1)

    def daily_summary(self, day: Optional[date] = None) -> dict:
        """Agregovaný denní přehled."""
        d = day or date.today()
        start = datetime.combine(d, datetime.min.time()).timestamp()
        end = start + 86400
        events = self.get_events(since_ts=start, until_ts=end, limit=500)
        counts = self.count_by_type(start)

        commits = counts.get("git.commit", 0)
        pushes = counts.get("git.push", 0)
        builds_ok = counts.get("build.success", 0) + counts.get("docker.build", 0)
        builds_fail = counts.get("build.fail", 0) + counts.get("docker.error", 0)
        commands = counts.get("command.run", 0) + counts.get("command.done", 0)
        releases = counts.get("release.create", 0)

        projects = self.get_projects(start)
        project_times = {
            p: self.estimate_project_time(p, start) for p in projects[:10]
        }
        total_hours = sum(project_times.values()) or round(
            len([e for e in events if e["type"] in ("app.focus", "app.open")]) * 5 / 60, 1
        )

        apps = [e for e in events if e["type"] in ("app.open", "app.focus")]
        apps_seen = list({e["title"] for e in apps if e["title"]})[:8]

        bugs = [
            e for e in events
            if e["type"] in ("build.fail", "docker.error", "command.error")
            or "fix" in e.get("detail", "").lower()
            or "bug" in e.get("detail", "").lower()
        ]

        lines = []
        if total_hours:
            main_proj = max(project_times, key=project_times.get) if project_times else ""
            if main_proj:
                lines.append(f"{total_hours}h práce na {main_proj}")
            else:
                lines.append(f"{total_hours}h práce dnes")
        if commits:
            lines.append(f"{commits} commit{'ů' if commits > 4 else 'y' if commits > 1 else ''}")
        if builds_fail:
            lines.append(f"{builds_fail} build{'y' if builds_fail > 1 else ''} selhal{'y' if builds_fail > 4 else ''}")
        if builds_ok:
            lines.append(f"{builds_ok} úspěšný{'ch' if builds_ok > 4 else 'ý' if builds_ok == 1 else 'é'} build{'ů' if builds_ok > 4 else 'y' if builds_ok > 1 else ''}")
        if releases:
            lines.append(f"{releases} release vytvořen{'y' if releases > 1 else ''}")
        if pushes:
            lines.append(f"{pushes} push na GitHub")

        return {
            "date": d.isoformat(),
            "summary": lines,
            "summary_text": "\n".join(f"• {l}" for l in lines) if lines else "Dnes zatím žádná aktivita.",
            "total_hours": total_hours,
            "commits": commits,
            "builds_failed": builds_fail,
            "builds_ok": builds_ok,
            "releases": releases,
            "commands": commands,
            "projects": project_times,
            "apps": apps_seen,
            "bugs": [{"title": b["title"], "detail": b["detail"], "ts": b["ts"]} for b in bugs[:10]],
            "events_count": len(events),
        }

    def query_natural(self, question: str) -> dict:
        """Odpověď na přirozené dotazy o aktivitě."""
        q = question.lower()
        today = self.daily_summary()
        week_start = (datetime.combine(date.today(), datetime.min.time())
                      - timedelta(days=7)).timestamp()

        if any(w in q for w in ("dnes", "today", "dělal")):
            return {"answer": today["summary_text"], "data": today}

        if any(w in q for w in ("týden", "week", "minulý")):
            counts = self.count_by_type(week_start)
            projects = self.get_projects(week_start)
            pt = {p: self.estimate_project_time(p, week_start) for p in projects}
            lines = [f"Za posledních 7 dní:"]
            if pt:
                for p, h in sorted(pt.items(), key=lambda x: -x[1])[:5]:
                    lines.append(f"• {p}: {h}h")
            if counts.get("git.commit"):
                lines.append(f"• {counts['git.commit']} commitů celkem")
            return {"answer": "\n".join(lines), "data": {"projects": pt, "counts": counts}}

        if any(w in q for w in ("skončil", "kde", "pokračovat", "left off")):
            recent = self.get_events(limit=5)
            if recent:
                last = recent[-1]
                return {
                    "answer": f"Naposledy: {last['title']} ({last['type']}) — {last['detail'][:120]}",
                    "data": {"last_event": last},
                }
            return {"answer": "Zatím nemám záznam poslední aktivity.", "data": {}}

        if any(w in q for w in ("bug", "chyb", "error", "fail")):
            events = self.get_events(since_ts=week_start, limit=200)
            bugs = [e for e in events if e["type"] in ("build.fail", "docker.error", "command.error")]
            if bugs:
                lines = [f"• {b['title']}: {b['detail'][:80]}" for b in bugs[-10:]]
                return {"answer": "Řešené problémy:\n" + "\n".join(lines), "data": {"bugs": bugs}}
            return {"answer": "Žádné zaznamenané chyby za poslední týden.", "data": {}}

        if any(w in q for w in ("čas", "time", "hodin")):
            projects = self.get_projects(week_start)
            pt = {p: self.estimate_project_time(p, week_start) for p in projects}
            if pt:
                lines = [f"• {p}: {h}h" for p, h in sorted(pt.items(), key=lambda x: -x[1])]
                return {"answer": "Čas na projektech (7 dní):\n" + "\n".join(lines), "data": pt}
            return {"answer": f"Dnes: {today['total_hours']}h práce.", "data": today}

        return {"answer": today["summary_text"], "data": today}


_store: Optional[ActivityStore] = None


def reset_activity_store() -> None:
    global _store
    _store = None


def get_activity_store() -> ActivityStore:
    global _store
    if _store is None:
        import os
        env = os.environ.get("JARVIS_ACTIVITY_DB")
        _store = ActivityStore(db_path=Path(env) if env else None)
    return _store
