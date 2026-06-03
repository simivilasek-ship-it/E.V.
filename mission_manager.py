"""
JARVIS — Mission Manager
Systém dlouhodobých autonomních misí s plánováním přes LLM, prováděním ReAct agentem
a vyhodnocením výsledků.

Schéma SQLite:
  missions        — metadata mise
  mission_steps   — kroky mise
  mission_events  — log událostí

API:
  get_mission_manager(config) → MissionManager  (singleton)
  list_missions()
  create_mission(title, description, deadline)
  pause_mission(mission_id)
  delete_mission(mission_id)
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── DB path ──────────────────────────────────────────────────────────────────
_DB_PATH = Path(__file__).parent / "memory_data" / "missions.db"

# ── Singleton ─────────────────────────────────────────────────────────────────
_instance: Optional["MissionManager"] = None
_instance_lock = threading.Lock()


# ─────────────────────────────────────────────────────────────────────────────
#  DB helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    """Vytvoří tabulky a indexy pokud neexistují."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS missions (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            description TEXT NOT NULL,
            deadline    TEXT,
            status      TEXT NOT NULL DEFAULT 'active',
            report      TEXT,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_missions_status ON missions(status);

        CREATE TABLE IF NOT EXISTS mission_steps (
            id          TEXT PRIMARY KEY,
            mission_id  TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
            description TEXT NOT NULL,
            due_date    TEXT,
            status      TEXT NOT NULL DEFAULT 'pending',
            result      TEXT,
            attempts    INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_steps_status    ON mission_steps(status);
        CREATE INDEX IF NOT EXISTS idx_steps_due_date  ON mission_steps(due_date);
        CREATE INDEX IF NOT EXISTS idx_steps_mission   ON mission_steps(mission_id);

        CREATE TABLE IF NOT EXISTS mission_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            mission_id  TEXT NOT NULL,
            step_id     TEXT,
            event_type  TEXT NOT NULL,
            message     TEXT,
            created_at  TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_events_mission ON mission_events(mission_id);
        """)
        conn.commit()


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def _log_event(conn: sqlite3.Connection, mission_id: str, event_type: str,
               message: str, step_id: Optional[str] = None) -> None:
    try:
        conn.execute(
            "INSERT INTO mission_events (mission_id, step_id, event_type, message, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (mission_id, step_id, event_type, message, _now()),
        )
    except Exception as e:
        logger.warning(f"mission_events log selhal: {e}")


# ─────────────────────────────────────────────────────────────────────────────
#  MissionPlanner
# ─────────────────────────────────────────────────────────────────────────────

class MissionPlanner:
    """Rozloží long-term úkol na kroky přes LLM."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self._config = config

    def _call_llm(self, prompt: str) -> str:
        try:
            import requests as _req
            url = self._config.get("ollama_url", "http://localhost:11434/api/chat")
            model = self._config.get("model", "llama3")
            resp = _req.post(
                url,
                json={"model": model, "messages": [{"role": "user", "content": prompt}],
                      "stream": False},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"MissionPlanner LLM volání selhalo: {e}")
            return ""

    def plan_steps(self, title: str, description: str,
                   deadline: Optional[str]) -> List[Dict[str, Any]]:
        """Vrátí seznam kroků jako list diktů."""
        deadline_hint = f"Termín splnění: {deadline}." if deadline else ""
        today = datetime.utcnow().date().isoformat()
        prompt = (
            f"Jsi asistent pro plánování dlouhodobých úkolů.\n"
            f"Dnešní datum: {today}\n"
            f"{deadline_hint}\n\n"
            f"Rozlož tento úkol na maximálně 10 konkrétních kroků, každý splnitelný za 1 den.\n"
            f"Úkol: {title}\nPopis: {description}\n\n"
            f"Odpověz POUZE jako JSON array, kde každý prvek má klíče:\n"
            f"  'description' (string) a 'due_date' (YYYY-MM-DD nebo null).\n"
            f"Příklad: [{{'description': 'Krok 1', 'due_date': '{today}'}}]\n"
            f"Nic jiného nepište."
        )
        raw = self._call_llm(prompt).strip()
        try:
            start = raw.index("[")
            end = raw.rindex("]") + 1
            steps_data = json.loads(raw[start:end])
            result = []
            for s in steps_data:
                if isinstance(s, dict) and "description" in s:
                    result.append({
                        "description": str(s["description"]),
                        "due_date": s.get("due_date"),
                    })
            if result:
                return result
        except Exception as e:
            logger.warning(f"Nepodařilo se parsovat kroky z LLM: {e} | raw={raw[:200]}")

        # Fallback — jeden krok
        return [{"description": description, "due_date": deadline}]

    def create_mission(self, title: str, description: str,
                       deadline: Optional[str] = None) -> Dict[str, Any]:
        """Uloží misi + kroky do DB, vrátí mission dict."""
        mission_id = str(uuid.uuid4())[:12]
        now = _now()

        steps_plan = self.plan_steps(title, description, deadline)

        with _get_conn() as conn:
            conn.execute(
                "INSERT INTO missions (id, title, description, deadline, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, 'active', ?, ?)",
                (mission_id, title, description, deadline, now, now),
            )
            step_rows = []
            for i, sp in enumerate(steps_plan):
                sid = f"{mission_id}-s{i+1}"
                conn.execute(
                    "INSERT INTO mission_steps "
                    "(id, mission_id, description, due_date, status, attempts, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, 'pending', 0, ?, ?)",
                    (sid, mission_id, sp["description"], sp.get("due_date"), now, now),
                )
                step_rows.append({
                    "id": sid,
                    "description": sp["description"],
                    "due_date": sp.get("due_date"),
                    "status": "pending",
                    "result": None,
                    "attempts": 0,
                })
            _log_event(conn, mission_id, "created",
                       f"Mise vytvořena s {len(step_rows)} kroky")
            conn.commit()

        logger.info(f"Mise '{title}' ({mission_id}) vytvořena s {len(step_rows)} kroky")
        return {
            "id": mission_id,
            "title": title,
            "description": description,
            "deadline": deadline,
            "status": "active",
            "steps": step_rows,
            "created_at": now,
        }


# ─────────────────────────────────────────────────────────────────────────────
#  MissionExecutor
# ─────────────────────────────────────────────────────────────────────────────

class MissionExecutor:
    """Provádí kroky misí na pozadí; voláno Schedulerem každých 15 min."""

    MAX_ATTEMPTS = 3

    def __init__(self, config: Dict[str, Any],
                 on_notify: Optional[Any] = None) -> None:
        self._config = config
        self._on_notify = on_notify

    def _notify(self, msg: str, urgency: str = "normal") -> None:
        try:
            if self._on_notify:
                self._on_notify(msg, urgency)
        except Exception:
            pass
        logger.info(f"[Mission Notify] {msg}")

    def _run_react(self, step_description: str) -> str:
        """Spustí ReAct agenta pro daný krok, vrátí textový výsledek."""
        try:
            from agent_react import ReactAgent
            agent = ReactAgent(config=self._config)
            result = agent.run(step_description)
            return result or "(prázdný výsledek)"
        except Exception as e:
            logger.error(f"ReAct agent selhal pro krok '{step_description[:60]}': {e}")
            return f"CHYBA: {e}"

    def _due_steps(self, conn: sqlite3.Connection) -> List[sqlite3.Row]:
        today = datetime.utcnow().date().isoformat()
        return conn.execute(
            """
            SELECT s.*, m.status AS mission_status
            FROM mission_steps s
            JOIN missions m ON m.id = s.mission_id
            WHERE s.status = 'pending'
              AND m.status = 'active'
              AND (s.due_date IS NULL OR s.due_date <= ?)
            ORDER BY s.due_date ASC
            LIMIT 20
            """,
            (today,),
        ).fetchall()

    def tick(self) -> None:
        """Zkontroluje a provede due kroky. Voláno Schedulerem."""
        try:
            with _get_conn() as conn:
                steps = self._due_steps(conn)
                conn.commit()

            logger.debug(f"MissionExecutor.tick: {len(steps)} kroků ke zpracování")

            for step in steps:
                self._execute_step(dict(step))
        except Exception as e:
            logger.error(f"MissionExecutor.tick selhal: {e}")

    def _execute_step(self, step: Dict[str, Any]) -> None:
        step_id = step["id"]
        mission_id = step["mission_id"]
        desc = step["description"]
        attempts = step["attempts"]

        logger.info(f"Provádím krok {step_id}: {desc[:80]}")

        now = _now()
        try:
            with _get_conn() as conn:
                conn.execute(
                    "UPDATE mission_steps SET status='running', attempts=?, updated_at=? WHERE id=?",
                    (attempts + 1, now, step_id),
                )
                _log_event(conn, mission_id, "step_started",
                           f"Pokus {attempts + 1}", step_id=step_id)
                conn.commit()
        except Exception as e:
            logger.error(f"DB update step running selhal: {e}")
            return

        result = self._run_react(desc)
        success = not result.startswith("CHYBA:")
        now = _now()
        new_attempts = attempts + 1

        try:
            with _get_conn() as conn:
                if success:
                    conn.execute(
                        "UPDATE mission_steps SET status='done', result=?, attempts=?, updated_at=? WHERE id=?",
                        (result, new_attempts, now, step_id),
                    )
                    _log_event(conn, mission_id, "step_done",
                               f"Krok úspěšný (pokus {new_attempts})", step_id=step_id)
                    logger.info(f"Krok {step_id} dokončen")
                else:
                    new_status = "failed" if new_attempts >= self.MAX_ATTEMPTS else "pending"
                    conn.execute(
                        "UPDATE mission_steps SET status=?, result=?, attempts=?, updated_at=? WHERE id=?",
                        (new_status, result, new_attempts, now, step_id),
                    )
                    _log_event(conn, mission_id, "step_failed",
                               f"Pokus {new_attempts} selhal: {result[:200]}", step_id=step_id)
                    if new_attempts >= self.MAX_ATTEMPTS:
                        conn.execute(
                            "UPDATE missions SET status='paused', updated_at=? WHERE id=?",
                            (now, mission_id),
                        )
                        _log_event(conn, mission_id, "mission_paused",
                                   f"Mise pauzována po {self.MAX_ATTEMPTS} neúspěšných pokusech")
                        conn.commit()
                        self._notify(
                            f"Mise pauzována: krok '{desc[:60]}' selhal {self.MAX_ATTEMPTS}x",
                            "high",
                        )
                        return
                conn.commit()
        except Exception as e:
            logger.error(f"DB update po kroku selhal: {e}")
            return

        self._check_completion(mission_id)

    def _check_completion(self, mission_id: str) -> None:
        try:
            with _get_conn() as conn:
                rows = conn.execute(
                    "SELECT status FROM mission_steps WHERE mission_id=?",
                    (mission_id,),
                ).fetchall()
            if not rows:
                return
            statuses = [r["status"] for r in rows]
            if all(s in ("done", "failed") for s in statuses):
                t = threading.Thread(
                    target=self._trigger_evaluation, args=(mission_id,), daemon=True
                )
                t.start()
        except Exception as e:
            logger.error(f"_check_completion selhal: {e}")

    def _trigger_evaluation(self, mission_id: str) -> None:
        try:
            evaluator = MissionEvaluator(self._config)
            evaluator.evaluate(mission_id)
        except Exception as e:
            logger.error(f"Evaluace mise {mission_id} selhala: {e}")


# ─────────────────────────────────────────────────────────────────────────────
#  MissionEvaluator
# ─────────────────────────────────────────────────────────────────────────────

class MissionEvaluator:
    """Po dokončení všech kroků vyhodnotí misi přes LLM."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self._config = config

    def _call_llm(self, prompt: str) -> str:
        try:
            import requests as _req
            url = self._config.get("ollama_url", "http://localhost:11434/api/chat")
            model = self._config.get("model", "llama3")
            resp = _req.post(
                url,
                json={"model": model, "messages": [{"role": "user", "content": prompt}],
                      "stream": False},
                timeout=90,
            )
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"MissionEvaluator LLM selhal: {e}")
            return ""

    def evaluate(self, mission_id: str) -> Dict[str, Any]:
        """Vyhodnotí misi a uloží report. Vrátí výsledek."""
        try:
            with _get_conn() as conn:
                mission_row = conn.execute(
                    "SELECT * FROM missions WHERE id=?", (mission_id,)
                ).fetchone()
                step_rows = conn.execute(
                    "SELECT * FROM mission_steps WHERE mission_id=? ORDER BY created_at",
                    (mission_id,),
                ).fetchall()

            if not mission_row:
                logger.warning(f"Mise {mission_id} nenalezena pro evaluaci")
                return {}

            mission = dict(mission_row)
            steps = [dict(s) for s in step_rows]

            steps_summary = "\n".join(
                f"- [{s['status'].upper()}] {s['description']}: {(s['result'] or '')[:200]}"
                for s in steps
            )
            prompt = (
                f"Vyhodnoť splnění mise a napiš závěrečný report.\n\n"
                f"Mise: {mission['title']}\n"
                f"Popis: {mission['description']}\n"
                f"Termín: {mission.get('deadline', 'neurčen')}\n\n"
                f"Výsledky kroků:\n{steps_summary}\n\n"
                f"Na základě výsledků urči:\n"
                f"1. Celkový výsledek: POUZE jedno ze slov: success / partial / failed\n"
                f"2. Stručný report (2–5 vět).\n\n"
                f"Formát odpovědi:\n"
                f"RESULT: <success|partial|failed>\n"
                f"REPORT: <text reportu>"
            )
            raw = self._call_llm(prompt)
            outcome = "partial"
            report = raw.strip()

            try:
                for line in raw.splitlines():
                    if line.startswith("RESULT:"):
                        val = line.split(":", 1)[1].strip().lower()
                        if val in ("success", "partial", "failed"):
                            outcome = val
                    if line.startswith("REPORT:"):
                        report = line.split(":", 1)[1].strip()
            except Exception:
                pass

            final_status = "done" if outcome in ("success", "partial") else "failed"
            now = _now()
            with _get_conn() as conn:
                conn.execute(
                    "UPDATE missions SET status=?, report=?, updated_at=? WHERE id=?",
                    (final_status, report, now, mission_id),
                )
                _log_event(conn, mission_id, "evaluated",
                           f"Výsledek: {outcome} | {report[:200]}")
                conn.commit()

            logger.info(f"Mise {mission_id} vyhodnocena: {outcome}")
            return {"mission_id": mission_id, "outcome": outcome, "report": report}
        except Exception as e:
            logger.error(f"MissionEvaluator.evaluate selhal: {e}")
            return {}


# ─────────────────────────────────────────────────────────────────────────────
#  MissionManager — fasáda
# ─────────────────────────────────────────────────────────────────────────────

class MissionManager:
    """Hlavní fasáda; inicializuje planner, executor, scheduler."""

    def __init__(self, config: Dict[str, Any],
                 on_notify: Optional[Any] = None) -> None:
        self._config = config
        self._on_notify = on_notify
        self._planner = MissionPlanner(config)
        self._executor = MissionExecutor(config, on_notify=on_notify)
        self._scheduler_task_id: Optional[str] = None
        _init_db()
        logger.info("MissionManager inicializován")

    # ── Scheduler ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Zaregistruje periodický tick do Scheduleru (každých 15 min)."""
        try:
            from scheduler import get_scheduler
            scheduler = get_scheduler()
            task = scheduler.every(900, self._executor.tick,
                                   name="mission_executor_tick")
            self._scheduler_task_id = getattr(task, "id", None)
            logger.info("MissionManager scheduler tick zaregistrován (každých 15 min)")
        except Exception as e:
            logger.warning(
                f"Nepodařilo se zaregistrovat scheduler tick: {e} — spouštím vlastní vlákno"
            )
            self._start_fallback_thread()

    def _start_fallback_thread(self) -> None:
        """Fallback: vlastní daemon vlákno pokud Scheduler není dostupný."""
        import time

        def _loop() -> None:
            while True:
                try:
                    self._executor.tick()
                except Exception as ex:
                    logger.error(f"mission tick selhal: {ex}")
                time.sleep(900)

        t = threading.Thread(target=_loop, daemon=True, name="mission-executor")
        t.start()

    def stop(self) -> None:
        try:
            if self._scheduler_task_id:
                from scheduler import get_scheduler
                get_scheduler().cancel(self._scheduler_task_id)
        except Exception:
            pass

    # ── Public API ───────────────────────────────────────────────────────────

    def create_mission(self, title: str, description: str,
                       deadline: Optional[str] = None) -> Dict[str, Any]:
        return self._planner.create_mission(title, description, deadline)

    def list_missions(self) -> List[Dict[str, Any]]:
        try:
            with _get_conn() as conn:
                missions = conn.execute(
                    "SELECT * FROM missions ORDER BY created_at DESC"
                ).fetchall()
                result = []
                for m in missions:
                    md = dict(m)
                    steps = conn.execute(
                        "SELECT id, description, due_date, status, result, attempts "
                        "FROM mission_steps WHERE mission_id=? ORDER BY created_at",
                        (md["id"],),
                    ).fetchall()
                    md["steps"] = [dict(s) for s in steps]
                    result.append(md)
                return result
        except Exception as e:
            logger.error(f"list_missions selhal: {e}")
            return []

    def get_mission(self, mission_id: str) -> Optional[Dict[str, Any]]:
        try:
            with _get_conn() as conn:
                m = conn.execute(
                    "SELECT * FROM missions WHERE id=?", (mission_id,)
                ).fetchone()
                if not m:
                    return None
                md = dict(m)
                steps = conn.execute(
                    "SELECT id, description, due_date, status, result, attempts "
                    "FROM mission_steps WHERE mission_id=? ORDER BY created_at",
                    (md["id"],),
                ).fetchall()
                md["steps"] = [dict(s) for s in steps]
                return md
        except Exception as e:
            logger.error(f"get_mission selhal: {e}")
            return None

    def pause_mission(self, mission_id: str) -> bool:
        try:
            now = _now()
            with _get_conn() as conn:
                cur = conn.execute(
                    "UPDATE missions SET status='paused', updated_at=? "
                    "WHERE id=? AND status='active'",
                    (now, mission_id),
                )
                if cur.rowcount:
                    _log_event(conn, mission_id, "paused",
                               "Mise pauzována uživatelem")
                    conn.commit()
                    return True
            return False
        except Exception as e:
            logger.error(f"pause_mission selhal: {e}")
            return False

    def resume_mission(self, mission_id: str) -> bool:
        try:
            now = _now()
            with _get_conn() as conn:
                cur = conn.execute(
                    "UPDATE missions SET status='active', updated_at=? "
                    "WHERE id=? AND status='paused'",
                    (now, mission_id),
                )
                if cur.rowcount:
                    _log_event(conn, mission_id, "resumed", "Mise obnovena")
                    conn.commit()
                    return True
            return False
        except Exception as e:
            logger.error(f"resume_mission selhal: {e}")
            return False

    def delete_mission(self, mission_id: str) -> bool:
        try:
            with _get_conn() as conn:
                cur = conn.execute(
                    "DELETE FROM missions WHERE id=?", (mission_id,)
                )
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            logger.error(f"delete_mission selhal: {e}")
            return False

    def get_events(self, mission_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            with _get_conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM mission_events WHERE mission_id=? "
                    "ORDER BY created_at DESC LIMIT ?",
                    (mission_id, limit),
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"get_events selhal: {e}")
            return []


# ─────────────────────────────────────────────────────────────────────────────
#  Singleton factory
# ─────────────────────────────────────────────────────────────────────────────

def get_mission_manager(config: Dict[str, Any],
                        on_notify: Optional[Any] = None) -> MissionManager:
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = MissionManager(config, on_notify=on_notify)
        return _instance


# ── Module-level convenience wrappers (pro import do dashboard.py) ────────────

def list_missions() -> List[Dict[str, Any]]:
    if _instance:
        return _instance.list_missions()
    return []


def create_mission(title: str, description: str,
                   deadline: Optional[str] = None) -> Dict[str, Any]:
    if _instance:
        return _instance.create_mission(title, description, deadline)
    raise RuntimeError(
        "MissionManager není inicializován — zavolej get_mission_manager() nejdříve"
    )


def pause_mission(mission_id: str) -> bool:
    if _instance:
        return _instance.pause_mission(mission_id)
    return False


def delete_mission(mission_id: str) -> bool:
    if _instance:
        return _instance.delete_mission(mission_id)
    return False
