"""
JARVIS — Activity Bridge
Propojuje EventBus, ActivityStore, Agent Timeline a WebSocket feed.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from activity_collector import get_activity_collector
from activity_store import get_activity_store
from event_bus import Event, EventType, get_event_bus

logger = logging.getLogger(__name__)

# Globální stav pro agent timeline a activity feed
_agent_timeline: List[dict] = []
_activity_feed: List[dict] = []
_proactive_suggestions: List[dict] = []
_broadcast_activity: Optional[Callable] = None
_broadcast_log: Optional[Callable] = None
_broadcast_graph: Optional[Callable] = None
_main_loop: Optional[asyncio.AbstractEventLoop] = None

MAX_TIMELINE = 30
MAX_FEED = 200
MAX_SUGGESTIONS = 20


def set_broadcasters(
    activity_fn: Optional[Callable] = None,
    log_fn: Optional[Callable] = None,
    graph_fn: Optional[Callable] = None,
    loop: Optional[asyncio.AbstractEventLoop] = None,
):
    global _broadcast_activity, _broadcast_log, _broadcast_graph, _main_loop
    if activity_fn is not None:
        _broadcast_activity = activity_fn
    if log_fn is not None:
        _broadcast_log = log_fn
    if graph_fn is not None:
        _broadcast_graph = graph_fn
    if loop is not None:
        _main_loop = loop


def get_agent_timeline() -> List[dict]:
    return _agent_timeline[-20:]


def get_activity_feed() -> List[dict]:
    return _activity_feed[-50:]


def get_proactive_suggestions() -> List[dict]:
    return _proactive_suggestions[-10:]


def _push_feed(event: dict):
    global _activity_feed
    entry = {
        **event,
        "ts": event.get("ts", time.time()),
        "time": time.strftime("%H:%M", time.localtime(event.get("ts", time.time()))),
    }
    _activity_feed.append(entry)
    if len(_activity_feed) > MAX_FEED:
        _activity_feed = _activity_feed[-MAX_FEED:]

    if _broadcast_activity and _main_loop:
        try:
            asyncio.run_coroutine_threadsafe(
                _broadcast_activity(entry), _main_loop)
        except Exception:
            pass


def _emit_log(message: str, level: str = "info"):
    if _broadcast_log and _main_loop:
        try:
            asyncio.run_coroutine_threadsafe(
                _broadcast_log(message, level), _main_loop)
        except Exception:
            pass


def record_agent_run_start(task: str, agent_type: str = "graph") -> str:
    run_id = f"run-{int(time.time() * 1000)}"
    run = {
        "id": run_id,
        "task": task,
        "agent_type": agent_type,
        "status": "running",
        "started_at": time.time(),
        "steps": [],
    }
    _agent_timeline.append(run)
    if len(_agent_timeline) > MAX_TIMELINE:
        _agent_timeline.pop(0)

    get_activity_store().record(
        "agent.run_start", title=task[:100],
        source=agent_type, meta={"run_id": run_id},
    )
    _push_feed({
        "type": "activity", "category": "agent",
        "message": f"Agent start: {task[:60]}",
        "level": "info",
    })
    return run_id


def record_agent_step(
    run_id: str,
    step_type: str,
    message: str,
    detail: str = "",
    tool: str = "",
    duration_ms: int = 0,
):
    for run in reversed(_agent_timeline):
        if run.get("id") == run_id:
            step = {
                "type": step_type,
                "message": message,
                "detail": detail,
                "tool": tool,
                "duration_ms": duration_ms,
                "status": "done",
            }
            run["steps"].append(step)
            break

    get_activity_collector().record_agent_step(step_type, message, detail)
    _push_feed({
        "type": "activity", "category": "agent",
        "message": f"{step_type}: {message[:80]}",
        "level": "info",
    })
    _emit_log(f"[Agent] {step_type}: {message}")

    if _broadcast_graph and _main_loop:
        try:
            asyncio.run_coroutine_threadsafe(
                _broadcast_graph({
                    "type": "node_enter",
                    "node": step_type,
                    "message": message,
                }),
                _main_loop,
            )
        except Exception:
            pass


def record_agent_run_end(run_id: str, answer: str = "", error: bool = False):
    for run in reversed(_agent_timeline):
        if run.get("id") == run_id:
            run["status"] = "error" if error else "done"
            run["answer"] = answer
            run["duration_ms"] = int((time.time() - run["started_at"]) * 1000)
            break

    etype = "agent.run_end"
    get_activity_store().record(
        etype, title="Agent dokončen" if not error else "Agent chyba",
        detail=answer[:300], source="agent",
        meta={"run_id": run_id, "error": error},
    )
    _push_feed({
        "type": "activity", "category": "agent",
        "message": "Agent dokončen" if not error else f"Agent chyba: {answer[:60]}",
        "level": "error" if error else "success",
    })


def add_proactive_suggestion(
    title: str,
    detail: str = "",
    action: str = "",
    action_label: str = "Otevřít",
    severity: str = "info",
):
    sug = {
        "id": f"sug-{int(time.time() * 1000)}",
        "title": title,
        "detail": detail,
        "action": action,
        "action_label": action_label,
        "severity": severity,
        "ts": time.time(),
        "time": time.strftime("%H:%M"),
    }
    _proactive_suggestions.append(sug)
    if len(_proactive_suggestions) > MAX_SUGGESTIONS:
        _proactive_suggestions.pop(0)

    get_activity_store().record(
        "proactive.suggestion", title=title, detail=detail,
        source="proactive", meta={"action": action, "severity": severity},
    )
    _push_feed({
        "type": "proactive", "category": "alert",
        "message": title,
        "detail": detail,
        "level": severity,
        "action": action,
        "action_label": action_label,
    })

    if severity in ("warning", "error", "critical"):
        try:
            from notification_engine import Notification, send_desktop_notification
            send_desktop_notification(Notification(
                title=f"JARVIS — {title}",
                body=detail or title,
                icon="dialog-warning" if severity == "warning" else "dialog-error",
                urgent=severity in ("error", "critical"),
            ))
        except Exception:
            pass


def _on_event(event: Event):
    """Centrální handler EventBus → ActivityStore + Feed."""
    store = get_activity_store()
    collector = get_activity_collector()
    data = event.data or {}

    mapping = {
        EventType.CPU_HIGH: ("proactive.alert", data.get("message", "CPU vysoké")),
        EventType.RAM_HIGH: ("proactive.alert", data.get("message", "RAM vysoká")),
        EventType.DISK_LOW: ("proactive.alert", data.get("message", "Disk plný")),
        EventType.TEMP_HIGH: ("proactive.alert", data.get("message", "Teplota vysoká")),
        EventType.AGENT_ALERT: ("proactive.alert", data.get("message", "Agent alert")),
        EventType.CMD_EXECUTE: ("command.run", data.get("text", str(data))[:100]),
        EventType.CMD_DONE: ("command.done", data.get("result", str(data))[:100]),
        EventType.CMD_ERROR: ("command.error", data.get("error", str(data))[:100]),
        EventType.LLM_START: ("llm.query", data.get("text", "")[:100]),
        EventType.LLM_DONE: ("llm.response", "LLM odpověď"),
        EventType.MEMORY_STORED: ("workspace.context", "Paměť uložena"),
    }

    if event.type in mapping:
        etype, title = mapping[event.type]
        store.record(etype, title=title, detail=str(data)[:200], source=event.source)

    if event.type in (EventType.CPU_HIGH, EventType.RAM_HIGH):
        msg = data.get("message", "")
        add_proactive_suggestion(
            title=msg,
            detail="Systém je přetížen. Chceš zobrazit procesy?",
            action="show_processes",
            action_label="Zobrazit procesy",
            severity="warning",
        )

    if event.type == EventType.AGENT_ALERT:
        add_proactive_suggestion(
            title=data.get("message", "Alert"),
            detail=data.get("detail", ""),
            severity="warning",
        )

    if event.type == EventType.GUI_COMMAND:
        text = data if isinstance(data, str) else data.get("text", "")
        if text:
            collector.record_command(text)

    # Build fail tracking → GitHub issue suggestion
    if event.type == EventType.CMD_ERROR or (
        isinstance(data, dict) and data.get("type") == "build.fail"
    ):
        count = data.get("count", 1) if isinstance(data, dict) else 1
        if count >= 3:
            add_proactive_suggestion(
                title=f"Build selhal {count}x",
                detail="Na GitHubu jsem našel podobný issue. Otevřít?",
                action="search_github_issues",
                action_label="Otevřít issue",
                severity="error",
            )

    _push_feed({
        "type": "event",
        "category": event.type,
        "message": str(data.get("message", event.type))[:120],
        "level": "warning" if "HIGH" in event.type or "ALERT" in event.type else "info",
        "source": event.source,
    })


_bridge_installed = False


def install_activity_bridge():
    global _bridge_installed
    if _bridge_installed:
        return
    bus = get_event_bus()
    bus.subscribe(EventType.ALL, _on_event)
    _bridge_installed = True
    logger.info("ActivityBridge nainstalován")
