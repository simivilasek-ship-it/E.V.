"""
JARVIS Workflow Engine
Uživatel definuje: "Když X → udělej Y"
Příklady:
  "Když je CPU > 90% → screenshot + notifikace"
  "Každý den v 9:00 → přečti dnešní zprávy"
  "Když otevřu VS Code → zapni tmavý režim"
"""
from __future__ import annotations
import datetime
import json
import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

WORKFLOWS_FILE = Path.home() / ".jarvis" / "workflows.json"


@dataclass
class Workflow:
    id: str
    name: str
    trigger_type: str        # "cpu_threshold" | "time" | "app_opened" | "manual" | "keyword"
    trigger_config: dict     # {"threshold": 90} | {"time": "09:00"} | {"app": "code"}
    action: str              # příkaz pro JARVIS (jako by ho uživatel řekl)
    enabled: bool = True
    last_fired: float = 0
    cooldown_seconds: int = 300  # minimální interval mezi spuštěními


class WorkflowEngine:
    """Spravuje a spouští workflow pravidla."""

    def __init__(self):
        self._workflows: dict[str, Workflow] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._action_callback: Optional[Callable[[str], None]] = None
        self._load()

    def set_action_callback(self, callback: Callable[[str], None]) -> None:
        """Nastaví callback pro spuštění příkazu (volá se při triggeru)."""
        self._action_callback = callback

    def add(self, workflow: Workflow) -> None:
        with self._lock:
            self._workflows[workflow.id] = workflow
        self._save()

    def remove(self, workflow_id: str) -> bool:
        with self._lock:
            if workflow_id in self._workflows:
                del self._workflows[workflow_id]
                self._save()
                return True
        return False

    def toggle(self, workflow_id: str) -> bool:
        with self._lock:
            if workflow_id in self._workflows:
                wf = self._workflows[workflow_id]
                wf.enabled = not wf.enabled
                self._save()
                return wf.enabled
        return False

    def list_all(self) -> list[dict]:
        with self._lock:
            return [asdict(w) for w in self._workflows.values()]

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="workflow-engine")
        self._thread.start()
        logger.info(f"WorkflowEngine spuštěn ({len(self._workflows)} workflows)")

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        while self._running:
            try:
                self._check_all()
            except Exception as e:
                logger.warning(f"WorkflowEngine loop chyba: {e}")
            time.sleep(5)  # Kontrola každých 5s

    def _check_all(self) -> None:
        import psutil
        now = time.time()
        with self._lock:
            workflows = list(self._workflows.values())

        for wf in workflows:
            if not wf.enabled:
                continue
            if now - wf.last_fired < wf.cooldown_seconds:
                continue
            try:
                if self._should_trigger(wf, psutil):
                    wf.last_fired = now
                    logger.info(f"Workflow triggered: {wf.name}")
                    if self._action_callback:
                        self._action_callback(wf.action)
            except Exception as e:
                logger.debug(f"Workflow check chyba ({wf.name}): {e}")

    def _should_trigger(self, wf: Workflow, psutil) -> bool:
        cfg = wf.trigger_config
        t = wf.trigger_type

        if t == "cpu_threshold":
            return psutil.cpu_percent(interval=0) >= cfg.get("threshold", 90)

        if t == "ram_threshold":
            return psutil.virtual_memory().percent >= cfg.get("threshold", 90)

        if t == "time":
            # "HH:MM" formát
            now_t = datetime.datetime.now().strftime("%H:%M")
            return now_t == cfg.get("time", "00:00")

        if t == "app_opened":
            import subprocess
            app = cfg.get("app", "")
            r = subprocess.run(["pgrep", "-x", app], capture_output=True, timeout=2)
            return r.returncode == 0

        return False

    def _save(self) -> None:
        try:
            WORKFLOWS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(WORKFLOWS_FILE, "w", encoding="utf-8") as f:
                json.dump([asdict(w) for w in self._workflows.values()], f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Workflow save chyba: {e}")

    def _load(self) -> None:
        try:
            if not WORKFLOWS_FILE.exists():
                return
            data = json.loads(WORKFLOWS_FILE.read_text(encoding="utf-8"))
            for d in data:
                wf = Workflow(**d)
                self._workflows[wf.id] = wf
            logger.info(f"Načteno {len(self._workflows)} workflows")
        except Exception as e:
            logger.warning(f"Workflow load chyba: {e}")


_engine: Optional[WorkflowEngine] = None

def get_workflow_engine() -> WorkflowEngine:
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine
