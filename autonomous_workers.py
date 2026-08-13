"""
E.V. — Autonomous Background Workers
Periodicky monitoruje e-mail, git repozitáře, kalendář a Slack.
Pokud detekuje důležitou událost, pošle proaktivní notifikaci uživateli.

Konfigurace v .env:
  IMAP_HOST=imap.gmail.com
  IMAP_USER=vas@gmail.com
  IMAP_PASS=app-password
  SLACK_BOT_TOKEN=xoxb-...
  CALENDAR_ICAL_URL=https://calendar.google.com/.../basic.ics
  GITHUB_TOKEN=ghp_...
  AUTO_WORKERS_INTERVAL=900   # sekundy mezi kontrolami (default 15 min)

Použití v app_core.py:
  from autonomous_workers import get_worker_manager
  mgr = get_worker_manager(config, on_notify=lambda msg: ...)
  mgr.start()
"""
from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


# ── Datové typy ───────────────────────────────────────────────────────────────

@dataclass
class WorkerEvent:
    source: str          # "email" | "git" | "calendar" | "slack" | "github"
    title: str
    body: str
    urgency: str = "low"   # low | medium | high
    action_hint: str = ""  # co E.V. může udělat


# ── Základní worker ───────────────────────────────────────────────────────────

class BaseWorker:
    """Abstraktní worker. Implementuj `check()` → List[WorkerEvent]."""

    name: str = "base"
    default_interval: int = 900  # sekundy

    def __init__(self, config: dict):
        self.config = config
        self.interval = int(config.get("auto_workers_interval",
                            os.getenv("AUTO_WORKERS_INTERVAL", self.default_interval)))
        self._last_run: float = 0.0

    def is_configured(self) -> bool:
        """Vrátí True pokud má worker potřebné přihlašovací údaje."""
        return False

    def check(self) -> List[WorkerEvent]:
        """Provede kontrolu a vrátí seznam nových událostí."""
        return []

    def should_run(self) -> bool:
        return time.time() - self._last_run >= self.interval

    def run(self) -> List[WorkerEvent]:
        if not self.is_configured():
            return []
        self._last_run = time.time()
        try:
            return self.check()
        except Exception as e:
            logger.warning(f"Worker {self.name} chyba: {e}")
            return []


# ── Email Worker (IMAP) ───────────────────────────────────────────────────────

class EmailWorker(BaseWorker):
    """Kontroluje nové e-maily přes IMAP. Filtruje důležité odesílatele."""

    name = "email"
    default_interval = 600  # 10 minut

    def __init__(self, config: dict):
        super().__init__(config)
        self._host     = config.get("imap_host") or os.getenv("IMAP_HOST", "")
        self._user     = config.get("imap_user") or os.getenv("IMAP_USER", "")
        self._password = config.get("imap_pass") or os.getenv("IMAP_PASS", "")
        self._seen_ids: set = set()
        self._keywords = ["urgentní", "urgent", "ASAP", "deadline", "important",
                          "důležité", "faktura", "invoice", "meeting", "schůzka"]

    def is_configured(self) -> bool:
        return bool(self._host and self._user and self._password)

    def check(self) -> List[WorkerEvent]:
        import imaplib
        import email as _email
        from email.header import decode_header

        events = []
        try:
            conn = imaplib.IMAP4_SSL(self._host, timeout=15)
            conn.login(self._user, self._password)
            conn.select("INBOX")

            # Hledej nepřečtené e-maily z posledních 24h
            since = (datetime.now() - timedelta(hours=24)).strftime("%d-%b-%Y")
            _, data = conn.search(None, f'(UNSEEN SINCE "{since}")')
            ids = (data[0] or b"").split()

            new_ids = [mid for mid in ids if mid not in self._seen_ids]
            self._seen_ids.update(ids)

            for mid in new_ids[:5]:  # max 5 najednou
                try:
                    _, msg_data = conn.fetch(mid, "(RFC822)")
                    msg = _email.message_from_bytes(msg_data[0][1])

                    # Dekóduj subject
                    subj_raw = msg.get("Subject", "")
                    subj_parts = decode_header(subj_raw)
                    subject = ""
                    for part, enc in subj_parts:
                        if isinstance(part, bytes):
                            subject += part.decode(enc or "utf-8", errors="replace")
                        else:
                            subject += str(part)

                    sender = msg.get("From", "")

                    # Urgentnost podle klíčových slov
                    urgency = "low"
                    combined = f"{subject} {sender}".lower()
                    if any(kw.lower() in combined for kw in self._keywords):
                        urgency = "high"

                    events.append(WorkerEvent(
                        source="email",
                        title=f"Nový e-mail: {subject[:60]}",
                        body=f"Od: {sender}\nPředmět: {subject}",
                        urgency=urgency,
                        action_hint="Chceš přečíst nebo odpovědět?",
                    ))
                except Exception as e:
                    logger.debug(f"Email parse chyba: {e}")

            conn.logout()
        except Exception as e:
            logger.warning(f"IMAP chyba: {e}")

        return events


# ── Git Worker ────────────────────────────────────────────────────────────────

class GitWorker(BaseWorker):
    """Monitoruje git repozitáře: nové commity, PR, neúspěšné testy."""

    name = "git"
    default_interval = 300  # 5 minut

    def __init__(self, config: dict):
        super().__init__(config)
        self._roots: List[str] = config.get("proactive_workspace_roots", [])
        if not self._roots:
            home = os.path.expanduser("~")
            # Auto-detekce: hledej git repozitáře v ~/Projects, ~/src, ~/code
            for candidate in ["Projects", "src", "code", "repos", "workspace"]:
                p = os.path.join(home, candidate)
                if os.path.isdir(p):
                    self._roots.append(p)
                    break
        self._seen_commits: dict = {}  # repo → set(hash)

    def is_configured(self) -> bool:
        return True  # vždy dostupné (git je lokální)

    def _find_git_repos(self, root: str, max_depth: int = 3) -> List[str]:
        repos = []
        try:
            for dirpath, dirnames, _ in os.walk(root):
                depth = dirpath[len(root):].count(os.sep)
                if depth >= max_depth:
                    dirnames.clear()
                    continue
                if ".git" in dirnames:
                    repos.append(dirpath)
                    dirnames.clear()  # neprocházej podadresáře git repozitáře
        except Exception:
            pass
        return repos[:10]  # max 10 repozitářů

    def check(self) -> List[WorkerEvent]:
        events = []
        for root in self._roots:
            for repo in self._find_git_repos(root):
                events.extend(self._check_repo(repo))
        return events

    def _check_repo(self, repo_path: str) -> List[WorkerEvent]:
        events = []
        try:
            # Nové commity na aktuální větvi (lokální)
            result = subprocess.run(
                ["git", "log", "--oneline", "--max-count=5", "--format=%H|%s|%an|%ar"],
                cwd=repo_path, capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                return []

            commits = [l for l in result.stdout.strip().splitlines() if "|" in l]
            repo_name = os.path.basename(repo_path)
            seen = self._seen_commits.setdefault(repo_path, set())

            for line in commits:
                parts = line.split("|", 3)
                if len(parts) < 4:
                    continue
                chash, subject, author, age = parts
                if chash in seen:
                    continue
                seen.add(chash)
                # Ignoruj staré commity (pouze nové po startu)
                if len(seen) > 5:  # první scan — jen zaznamenej, nenotifikuj
                    events.append(WorkerEvent(
                        source="git",
                        title=f"Nový commit v {repo_name}",
                        body=f"{author}: {subject}\n({age})",
                        urgency="low",
                        action_hint=f"Chceš si prohlédnout diff? (repo: {repo_path})",
                    ))

            # Detekce neúspěšných testů (pytest/jest výstup v posledním commitu)
            result2 = subprocess.run(
                ["git", "log", "-1", "--format=%B"],
                cwd=repo_path, capture_output=True, text=True, timeout=5,
            )
            if result2.returncode == 0:
                msg = result2.stdout.lower()
                if any(kw in msg for kw in ["fix:", "hotfix:", "broken", "failing", "error:"]):
                    events.append(WorkerEvent(
                        source="git",
                        title=f"Potenciální oprava chyby v {repo_name}",
                        body=result2.stdout.strip()[:200],
                        urgency="medium",
                        action_hint="Chceš spustit testy?",
                    ))

        except Exception as e:
            logger.debug(f"Git worker chyba ({repo_path}): {e}")
        return events


# ── Calendar Worker (iCal) ────────────────────────────────────────────────────

class CalendarWorker(BaseWorker):
    """Načítá iCal URL a upozorní na blížící se události (< 30 min)."""

    name = "calendar"
    default_interval = 300

    def __init__(self, config: dict):
        super().__init__(config)
        self._ical_url = (config.get("calendar_ical_url")
                          or os.getenv("CALENDAR_ICAL_URL", ""))
        self._notified_events: set = set()

    def is_configured(self) -> bool:
        return bool(self._ical_url)

    def check(self) -> List[WorkerEvent]:
        try:
            import requests as _req
            from datetime import timezone
        except ImportError:
            return []

        events = []
        try:
            resp = _req.get(self._ical_url, timeout=15)
            resp.raise_for_status()
            text = resp.text
        except Exception as e:
            logger.warning(f"iCal načtení selhalo: {e}")
            return []

        now = datetime.now()
        window_end = now + timedelta(minutes=30)

        # Jednoduchý iCal parser (bez icalendar knihovny)
        import re
        events_raw = re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", text, re.DOTALL)
        for ev_raw in events_raw:
            try:
                summary_m = re.search(r"SUMMARY:(.*?)(?:\r?\n)", ev_raw)
                dtstart_m = re.search(r"DTSTART(?:;[^:]+)?:(.*?)(?:\r?\n)", ev_raw)
                uid_m     = re.search(r"UID:(.*?)(?:\r?\n)", ev_raw)

                if not (summary_m and dtstart_m):
                    continue

                summary  = summary_m.group(1).strip()
                uid      = uid_m.group(1).strip() if uid_m else summary
                dt_str   = dtstart_m.group(1).strip()

                # Parsuj datetime (YYYYMMDDTHHMMSS nebo YYYYMMDD)
                try:
                    if "T" in dt_str:
                        dt = datetime.strptime(dt_str[:15], "%Y%m%dT%H%M%S")
                    else:
                        dt = datetime.strptime(dt_str[:8], "%Y%m%d")
                except ValueError:
                    continue

                if now <= dt <= window_end and uid not in self._notified_events:
                    self._notified_events.add(uid)
                    minutes_left = int((dt - now).total_seconds() / 60)
                    events.append(WorkerEvent(
                        source="calendar",
                        title=f"Blíží se událost: {summary}",
                        body=f"Začátek za {minutes_left} minut ({dt.strftime('%H:%M')})",
                        urgency="high" if minutes_left <= 10 else "medium",
                        action_hint="Chceš připravit podklady nebo nastavit připomínku?",
                    ))
            except Exception:
                continue

        return events


# ── Slack Worker ──────────────────────────────────────────────────────────────

class SlackWorker(BaseWorker):
    """Čte nepřečtené zprávy ze Slacku přes Bot Token."""

    name = "slack"
    default_interval = 300

    def __init__(self, config: dict):
        super().__init__(config)
        self._token   = config.get("slack_bot_token") or os.getenv("SLACK_BOT_TOKEN", "")
        self._user_id = ""
        self._seen_ts: dict = {}   # channel_id → set(ts)
        self._keywords = ["změna", "change", "deadline", "urgent", "asap",
                          "prosím", "přijď", "review", "pr", "bug", "hotfix"]

    def is_configured(self) -> bool:
        return bool(self._token)

    def _get_user_id(self) -> str:
        if self._user_id:
            return self._user_id
        try:
            import requests as _req
            r = _req.get("https://slack.com/api/auth.test",
                         headers={"Authorization": f"Bearer {self._token}"}, timeout=10)
            self._user_id = r.json().get("user_id", "")
        except Exception:
            pass
        return self._user_id

    def check(self) -> List[WorkerEvent]:
        try:
            import requests as _req
        except ImportError:
            return []

        events = []
        uid = self._get_user_id()
        if not uid:
            return []

        try:
            # Získej seznam kanálů
            r = _req.get(
                "https://slack.com/api/conversations.list",
                headers={"Authorization": f"Bearer {self._token}"},
                params={"limit": 20, "types": "public_channel,private_channel,im"},
                timeout=10,
            )
            channels = r.json().get("channels", [])
        except Exception as e:
            logger.warning(f"Slack channels selhalo: {e}")
            return []

        for ch in channels[:10]:
            cid   = ch.get("id", "")
            cname = ch.get("name", ch.get("user", cid))
            seen  = self._seen_ts.setdefault(cid, set())

            try:
                r2 = _req.get(
                    "https://slack.com/api/conversations.history",
                    headers={"Authorization": f"Bearer {self._token}"},
                    params={"channel": cid, "limit": 10},
                    timeout=10,
                )
                msgs = r2.json().get("messages", [])
            except Exception:
                continue

            for msg in msgs:
                ts   = msg.get("ts", "")
                text = msg.get("text", "")
                muid = msg.get("user", "")

                if ts in seen or muid == uid:
                    continue
                seen.add(ts)

                # Filtr na klíčová slova nebo přímé zmínky
                lower = text.lower()
                is_mention  = f"<@{uid}>" in text
                is_keyword  = any(kw in lower for kw in self._keywords)

                if not (is_mention or is_keyword):
                    continue

                urgency = "high" if is_mention else "medium"
                events.append(WorkerEvent(
                    source="slack",
                    title=f"Slack zpráva v #{cname}",
                    body=text[:300],
                    urgency=urgency,
                    action_hint="Chceš odpovědět nebo otevřít Slack?",
                ))

        return events


# ── GitHub Worker ─────────────────────────────────────────────────────────────

class GitHubWorker(BaseWorker):
    """Monitoruje GitHub notifikace (PR, issues, zmínky)."""

    name = "github"
    default_interval = 600

    def __init__(self, config: dict):
        super().__init__(config)
        self._token   = config.get("github_token") or os.getenv("GITHUB_TOKEN", "")
        self._seen_ids: set = set()

    def is_configured(self) -> bool:
        return bool(self._token)

    def check(self) -> List[WorkerEvent]:
        try:
            import requests as _req
        except ImportError:
            return []

        events = []
        try:
            r = _req.get(
                "https://api.github.com/notifications",
                headers={"Authorization": f"token {self._token}",
                         "Accept": "application/vnd.github.v3+json"},
                params={"all": False, "per_page": 20},
                timeout=15,
            )
            r.raise_for_status()
            notifications = r.json()
        except Exception as e:
            logger.warning(f"GitHub notifications selhalo: {e}")
            return []

        for notif in notifications:
            nid    = str(notif.get("id", ""))
            reason = notif.get("reason", "")
            title  = notif.get("subject", {}).get("title", "")
            ntype  = notif.get("subject", {}).get("type", "")
            repo   = notif.get("repository", {}).get("full_name", "")

            if nid in self._seen_ids:
                continue
            self._seen_ids.add(nid)

            urgency_map = {
                "mention": "high",
                "review_requested": "high",
                "assign": "medium",
                "comment": "low",
            }
            urgency = urgency_map.get(reason, "low")

            events.append(WorkerEvent(
                source="github",
                title=f"GitHub {ntype}: {title[:50]}",
                body=f"Repozitář: {repo}\nDůvod: {reason}",
                urgency=urgency,
                action_hint="Chceš otevřít v prohlížeči?",
            ))

        return events


# ── Worker Manager ────────────────────────────────────────────────────────────

class WorkerManager:
    """
    Orchestrátor všech background workerů.
    Spouští periodické kontroly a volá on_notify callback pro notifikace.

    on_notify(message: str, urgency: str) — callback volaný při nové události
    """

    def __init__(self, config: dict,
                 on_notify: Callable[[str, str], None] = None):
        self.config    = config
        self._notify   = on_notify or (lambda msg, urg: logger.info(f"[{urg}] {msg}"))
        self._workers  = self._init_workers(config)
        self._thread:  Optional[threading.Thread] = None
        self._running  = False
        self._tick_interval = 30  # kontrola každých 30s zda má worker běžet

    def _init_workers(self, config: dict) -> List[BaseWorker]:
        workers = [
            GitWorker(config),     # vždy aktivní
            EmailWorker(config),
            CalendarWorker(config),
            SlackWorker(config),
            GitHubWorker(config),
        ]
        active = [w for w in workers if w.is_configured()]
        logger.info(f"AutonomousWorkers: {[w.name for w in active]}")
        return active

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="AutonomousWorkers")
        self._thread.start()
        logger.info("AutonomousWorkers spuštěny")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _loop(self):
        while self._running:
            for worker in self._workers:
                if not self._running:
                    break
                if not worker.should_run():
                    continue
                events = worker.run()
                for ev in events:
                    self._dispatch(ev)
            time.sleep(self._tick_interval)

    def _dispatch(self, ev: WorkerEvent):
        """Zformátuje událost a pošle notifikaci."""
        try:
            # Zkusí využít LLM pro chytřejší shrnutí high-urgency událostí
            summary = ev.body
            if ev.urgency == "high":
                try:
                    summary = self._llm_summarize(ev)
                except Exception:
                    pass

            msg = f"[{ev.source.upper()}] {ev.title}\n{summary}"
            if ev.action_hint:
                msg += f"\n→ {ev.action_hint}"

            self._notify(msg, ev.urgency)
            logger.info(f"Worker event [{ev.urgency}] {ev.source}: {ev.title}")
        except Exception as e:
            logger.warning(f"Worker dispatch chyba: {e}")

    def _llm_summarize(self, ev: WorkerEvent) -> str:
        """Použije cloud LLM pro shrnutí důležité události."""
        try:
            from cloud_router import get_cloud_router
            cloud = get_cloud_router(self.config)
            if not cloud.enabled:
                return ev.body
            messages = [{
                "role": "user",
                "content": (
                    f"Shrň tuto událost v 1-2 větách česky a navrhni, co by měl uživatel udělat:\n"
                    f"Zdroj: {ev.source}\nNázev: {ev.title}\nDetail: {ev.body}"
                )
            }]
            resp = cloud.call(messages, task_type="fast", temperature=0.3, max_tokens=150)
            return resp.content
        except Exception:
            return ev.body

    def run_now(self, worker_name: str) -> List[WorkerEvent]:
        """Okamžitě spustí konkrétní worker (pro manuální spuštění)."""
        for w in self._workers:
            if w.name == worker_name:
                w._last_run = 0.0
                return w.run()
        return []

    def status(self) -> dict:
        return {
            "running": self._running,
            "workers": [
                {
                    "name": w.name,
                    "configured": w.is_configured(),
                    "interval_s": w.interval,
                    "next_run_in": max(0, int(w.interval - (time.time() - w._last_run))),
                }
                for w in self._workers
            ],
        }


# Singleton
_manager: Optional[WorkerManager] = None


def get_worker_manager(
    config: dict = None,
    on_notify: Callable[[str, str], None] = None,
) -> WorkerManager:
    global _manager
    if _manager is None:
        if config is None:
            try:
                from config import CONFIG
                config = CONFIG
            except Exception:
                config = {}
        _manager = WorkerManager(config, on_notify=on_notify)
    return _manager
