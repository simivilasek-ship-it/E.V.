"""
E.V. — Routing pipeline
Vyčleněno z app_core.py pro lepší čitelnost a testovatelnost.

CommandRouter zpracovává příkaz v pořadí:
  offline check → plugin routes → local router → graf agent
  → react agent → LLM (streaming)
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Optional, Tuple

if TYPE_CHECKING:
    from app_core import EVApp

logger = logging.getLogger(__name__)


def _classify_mode(text: str) -> str:
    """Vrátí 'agent' | 'action' | 'copilot' pro status v UI."""
    try:
        from agent_hierarchical import should_handle as _h
        from agent_graph import should_handle as _g
        from agent_react import should_handle as _r
        if _h(text) or _g(text) or _r(text):
            return "agent"
    except Exception:
        pass
    try:
        from local_router import LocalRouter
        _, act = LocalRouter().route(text)
        if act is not None:
            return "action"
    except Exception:
        pass
    return "copilot"


_MODE_STATUS = {
    "agent":   "🤖 Agent pracuje…",
    "action":  "⚡ Provádím akci…",
    "copilot": "💬 Copilot…",
}


def _agent_plan_preview(text: str) -> str:
    """Jednořádkový náhled plánu pro web UI před spuštěním agenta."""
    first = (text or "").strip().split("\n", 1)[0].strip()
    if 12 <= len(first) <= 140:
        snippet = first if len(first) <= 100 else first[:97] + "…"
        return f"Plán: 1) {snippet}"
    return "Plán: Zpracovávám vícekrokový úkol…"


class CommandRouter:
    """Zapouzdřuje routing logiku — nezávislá na GUI lifecycle."""

    def __init__(self, app: "EVApp"):
        self._app = app

    # ── Veřejné API ───────────────────────────────────

    def process(self, text: str) -> None:
        """Hlavní vstupní bod. Volá se z app_core._process_command()."""
        app = self._app
        app._gui(lambda: app.gui.add_message(text, "user"))
        app._gui(lambda: app.gui.set_state("thinking"))
        app._gui(lambda: app.gui.set_status("Zpracovávám..."))
        try:
            if not self._fast_path(text):
                self._llm_path(text)
        except Exception as e:
            logger.error(f"Chyba zpracování: {e}", exc_info=True)
            from error_handling import ErrorSeverity, ErrorCategory
            app.error_handler.log_error(
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.SYSTEM,
                source="CommandRouter.process",
                message=str(e), exception=e,
            )
            app._gui(lambda: app.gui.add_message("Chyba. Zkus to znovu.", "jarvis"))
        finally:
            app._gui(lambda: app.gui.set_state("idle"))
            app._gui(lambda: app.gui.set_status(""))

    def process_for_web(
        self,
        text: str,
        *,
        on_chunk: Callable[[str], None] | None = None,
        on_agent_step: Callable[[str], None] | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> str:
        """Web/API vstup — stejný pipeline jako desktop, bez TTS, se streamingem."""
        app = self._app
        replies: list[str] = []
        orig_add = app.gui.add_message
        orig_status = app.gui.set_status
        orig_state = app.gui.set_state

        def _capture_add(msg: str, sender: str = "jarvis") -> None:
            if sender == "jarvis" and msg:
                replies.append(msg)

        def _capture_status(status: str) -> None:
            if not status:
                return
            if on_status:
                on_status(status)
            if status.startswith("↳"):
                replies.append(status.lstrip("↳ ").strip())
            elif status.startswith("⚠"):
                replies.append(status)

        app.gui.add_message = _capture_add
        app.gui.set_status = _capture_status
        app.gui.set_state = lambda _s: None

        try:
            mode = _classify_mode(text)
            if on_status and mode != "copilot":
                on_status(_MODE_STATUS[mode])

            if self._fast_path_web(text, on_agent_step):
                final = replies[-1] if replies else "Hotovo."
                if on_chunk and final:
                    on_chunk(final)
                return final

            offline = self._offline_response(text)
            if offline:
                if on_chunk:
                    on_chunk(offline)
                app._execute_result(offline, {"action": "answer", "params": {}}, speak=False)
                return offline

            if not app._ollama_reachable():
                msg = (
                    "Ollama není dostupná. Lokální příkazy fungují — "
                    "zkus 'kolik je hodin', 'otevři chrome' nebo 'co mám na obrazovce'."
                )
                if on_chunk:
                    on_chunk(msg)
                return msg

            if on_status:
                on_status(_MODE_STATUS["copilot"])

            from agent_tools import build_copilot_registry

            copilot_reg = build_copilot_registry(
                app.cmds, getattr(app, "mcp", None))
            tools_schema = copilot_reg.ollama_tools_schema()

            def _on_tool_call(name: str, args: dict) -> str:
                tool = copilot_reg.get(name)
                if tool is None:
                    return f"Nástroj '{name}' neexistuje"
                return tool.call(**args)

            tool_result = app.llm.try_copilot_tools(
                text, tools_schema, _on_tool_call)
            if tool_result is not None:
                if on_chunk:
                    on_chunk(tool_result)
                return tool_result

            full = ""
            for chunk in app.llm.stream_ask(text):
                if not isinstance(chunk, str) or not chunk:
                    continue
                full += chunk
                if on_chunk:
                    on_chunk(chunk)
                if "COMMAND:" in full:
                    break

            if "COMMAND:" in full:
                for extra in app.llm.drain_stream():
                    full += extra

            full = full.strip()
            if full and not full.startswith("COMMAND:"):
                return full

            return replies[-1] if replies else (full or "OK")
        except Exception as e:
            logger.error(f"process_for_web: {e}", exc_info=True)
            err = f"Chyba zpracování: {e}"
            if on_chunk:
                on_chunk(err)
            return err
        finally:
            app.gui.add_message = orig_add
            app.gui.set_status = orig_status
            app.gui.set_state = orig_state
            try:
                app.llm.save_history()
            except Exception:
                pass

    def _fast_path_web(
        self,
        text: str,
        on_agent_step: Callable[[str], None] | None,
    ) -> bool:
        """Stejný fast path jako desktop, s agent step callbackem pro web UI."""
        app = self._app

        # Lokální router má prioritu — deterministické příkazy bez MCP
        msg, action_data = app.llm.quick_match(text)
        if action_data is not None:
            app._execute_result(msg, action_data, speak=False)
            return True

        if app.plugin_manager:
            result = self._plugin_routes(text)
            if result:
                app._execute_result(*result, speak=False)
                return True

        def _step_cb(step_text: str, step_type: str = "agent") -> None:
            if on_agent_step and step_text:
                on_agent_step(step_text)

        from agent_hierarchical import should_handle as _hierarchical_should
        if getattr(app, "hierarchical_agent", None) and _hierarchical_should(text):
            import time as _t, uuid as _uuid
            if on_agent_step:
                on_agent_step(_agent_plan_preview(text))
            app.gui.set_status("Supervisor plánuje…")
            steps: list = []
            t0 = _t.time()
            answer = app.hierarchical_agent.run(
                text,
                on_step=lambda s: (
                    steps.append({"type": "hierarchical", "text": s, "ts": _t.time()}),
                    _step_cb(s),
                    app.gui.set_status(s),
                ),
            )
            self._save_run(str(_uuid.uuid4())[:8], text, steps, answer, "done", round(_t.time() - t0, 2))
            app._execute_result(answer, {"action": "answer", "params": {}}, speak=False)
            return True

        from agent_graph import should_handle as _graph_should
        if getattr(app, "graph_agent", None) and _graph_should(text):
            import time as _t, uuid as _uuid
            if on_agent_step:
                on_agent_step(_agent_plan_preview(text))
            app.gui.set_status("Agent plánuje…")
            steps: list = []
            t0 = _t.time()
            answer = app.graph_agent.run(
                text,
                on_step=lambda s: (
                    steps.append({"type": "plan", "text": s, "ts": _t.time()}),
                    _step_cb(s, "plan"),
                    app.gui.set_status(s),
                ),
            )
            self._save_run(str(_uuid.uuid4())[:8], text, steps, answer, "done", round(_t.time() - t0, 2))
            app._execute_result(answer, {"action": "answer", "params": {}}, speak=False)
            return True

        from agent_react import should_handle as _react_should
        if getattr(app, "react_agent", None) and _react_should(text):
            import time as _t, uuid as _uuid
            if on_agent_step:
                on_agent_step(_agent_plan_preview(text))
            app.gui.set_status("Agent pracuje…")
            steps: list = []
            t0 = _t.time()
            answer = app.react_agent.run_with_tool_calling(
                text,
                on_step=lambda s: (
                    steps.append({"type": "react", "text": s, "ts": _t.time()}),
                    _step_cb(s, "react"),
                    app.gui.set_status(s),
                ),
            )
            self._save_run(str(_uuid.uuid4())[:8], text, steps, answer, "done", round(_t.time() - t0, 2))
            app._execute_result(answer, {"action": "answer", "params": {}}, speak=False)
            return True

        return False

    # ── Offline check ─────────────────────────────────

    def _offline_response(self, text: str) -> Optional[str]:
        """Vrátí offline odpověď pokud je systém offline, jinak None."""
        try:
            from offline_mode import get_offline_manager, OfflineStatus
            mgr = get_offline_manager(self._app.llm.config)
            if mgr.get_status() in (OfflineStatus.OFFLINE, OfflineStatus.DEGRADED):
                # Zkus nejdřív local router — ten funguje vždy
                msg, action = self._app.llm.quick_match(text)
                if action is not None:
                    return None  # local router to zvládne, nechejme ho
                return mgr.get_offline_response(text)
        except Exception:
            pass
        return None

    # ── Fast path ─────────────────────────────────────

    def _fast_path(self, text: str) -> bool:
        """Plugin → local router → agenti. Vrátí True pokud obslouženo."""
        app = self._app

        # 0. Offline check (jen pro LLM cestu — local router vždy funguje)
        # (zpracováno v _llm_path)

        # 1. Lokální router (priorita před pluginy)
        msg, action_data = app.llm.quick_match(text)
        if action_data is not None:
            app._execute_result(msg, action_data)
            return True

        # 2. Plugin routes (MCP rozšíření)
        if app.plugin_manager:
            result = self._plugin_routes(text)
            if result:
                app._execute_result(*result)
                return True

        # 2b. Hierarchický agent
        from agent_hierarchical import should_handle as _hierarchical_should
        if getattr(app, "hierarchical_agent", None) and _hierarchical_should(text):
            import time as _t, uuid as _uuid
            app._gui(lambda: app.gui.set_status("Supervisor plánuje…"))
            steps: list = []
            t0 = _t.time()
            answer = app.hierarchical_agent.run(
                text,
                on_step=lambda s: (
                    steps.append({"type": "hierarchical", "text": s, "ts": _t.time()}),
                    app._gui(lambda m=s: app.gui.set_status(m)),
                ))
            self._save_run(str(_uuid.uuid4())[:8], text, steps, answer,
                           "done", round(_t.time() - t0, 2))
            app._execute_result(answer, {"action": "answer", "params": {}})
            return True

        # 3. Grafový agent
        from agent_graph import should_handle as _graph_should
        if getattr(app, "graph_agent", None) and _graph_should(text):
            import time as _t, uuid as _uuid
            app._gui(lambda: app.gui.set_status("Plánovač přemýšlí…"))
            steps: list = []
            t0 = _t.time()
            answer = app.graph_agent.run(
                text,
                on_step=lambda s: (
                    steps.append({"type": "plan", "text": s, "ts": _t.time()}),
                    app._gui(lambda m=s: app.gui.set_status(m)),
                ))
            self._save_run(str(_uuid.uuid4())[:8], text, steps, answer,
                           "done", round(_t.time() - t0, 2))
            app._execute_result(answer, {"action": "answer", "params": {}})
            return True

        # 4. ReAct agent — preferuje Ollama tool-calling, fallback na regex ReAct
        from agent_react import should_handle as _react_should
        if getattr(app, "react_agent", None) and _react_should(text):
            import time as _t, uuid as _uuid
            app._gui(lambda: app.gui.set_status("Agent přemýšlí…"))
            steps: list = []
            t0 = _t.time()
            # run_with_tool_calling automaticky fallbackne na run() pokud model nepodporuje tools
            answer = app.react_agent.run_with_tool_calling(
                text,
                on_step=lambda s: (
                    steps.append({"type": "react", "text": s, "ts": _t.time()}),
                    app._gui(lambda m=s: app.gui.set_status(m)),
                ))
            self._save_run(str(_uuid.uuid4())[:8], text, steps, answer,
                           "done", round(_t.time() - t0, 2))
            app._execute_result(answer, {"action": "answer", "params": {}})
            return True

        return False

    def _llm_path(self, text: str) -> None:
        """Streaming LLM cesta s offline fallbackem."""
        app = self._app

        # Offline fallback před LLM voláním
        offline_reply = self._offline_response(text)
        if offline_reply:
            app._execute_result(offline_reply, {"action": "answer", "params": {}})
            return

        if not app._ollama_reachable():
            app._execute_result(
                "Ollama není dostupná. Lokální příkazy fungují — "
                "zkus 'kolik je hodin', 'otevři chrome' nebo 'hlasitost na 50'.",
                {"action": "answer", "params": {}},
            )
            return

        full_response = ""
        is_command    = False

        def _collecting():
            nonlocal full_response, is_command
            for chunk in app.llm.stream_ask(text):
                full_response += chunk
                if "COMMAND:" in full_response:
                    is_command = True
                    return
                yield chunk

        app.tts.speak_streaming(_collecting())

        if is_command:
            for chunk in app.llm.drain_stream():
                full_response += chunk

        full_text = full_response.strip()
        if full_text:
            app._execute_result(full_text, {"action": "answer", "params": {}},
                                speak=False)

    def _save_run(self, run_id: str, task: str, steps: list,
                  result: str, status: str, duration: float) -> None:
        """Uloží agentský run do SQLite přes dashboard API (fire-and-forget)."""
        try:
            import threading, json, urllib.request
            data = json.dumps({
                "id": run_id, "task": task, "steps": steps,
                "result": result[:500], "status": status, "duration": duration,
            }).encode()
            req = urllib.request.Request(
                "http://127.0.0.1:8002/api/agent/timeline",
                data=data, method="POST",
                headers={"Content-Type": "application/json"},
            )
            threading.Thread(
                target=lambda: urllib.request.urlopen(req, timeout=2),
                daemon=True).start()
        except Exception:
            pass

    def _plugin_routes(self, text: str) -> Optional[Tuple[str, dict]]:
        app = self._app
        for route in app.plugin_manager.get_routes():
            try:
                pattern     = route.get("pattern")
                handler     = route.get("handler")
                plugin_name = route.get("plugin", "?")
                if pattern and handler and pattern.search(text):
                    result = app.plugin_manager.call_route(
                        handler, text, plugin_name=plugin_name)
                    if result and result[0] is not None:
                        return result
            except Exception as e:
                logger.debug(f"Plugin route selhala: {e}")
        return None
