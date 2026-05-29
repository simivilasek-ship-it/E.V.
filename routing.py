"""
JARVIS — Routing pipeline
Vyčleněno z app_core.py pro lepší čitelnost a testovatelnost.

CommandRouter zpracovává příkaz v pořadí:
  offline check → plugin routes → local router → graf agent
  → react agent → LLM (streaming)
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from app_core import JarvisApp

logger = logging.getLogger(__name__)


class CommandRouter:
    """Zapouzdřuje routing logiku — nezávislá na GUI lifecycle."""

    def __init__(self, app: "JarvisApp"):
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

        # 1. Plugin routes
        if app.plugin_manager:
            result = self._plugin_routes(text)
            if result:
                app._execute_result(*result)
                return True

        # 2. Lokální router
        msg, action_data = app.llm.quick_match(text)
        if action_data is not None:
            app._execute_result(msg, action_data)
            return True

        # 3. Grafový agent
        from agent_graph import should_handle as _graph_should
        if getattr(app, "graph_agent", None) and _graph_should(text):
            app._gui(lambda: app.gui.set_status("Plánovač přemýšlí…"))
            answer = app.graph_agent.run(
                text,
                on_step=lambda s: app._gui(lambda m=s: app.gui.set_status(m)))
            app._execute_result(answer, {"action": "answer", "params": {}})
            return True

        # 4. ReAct agent
        from agent_react import should_handle as _react_should
        if getattr(app, "react_agent", None) and _react_should(text):
            app._gui(lambda: app.gui.set_status("Agent přemýšlí…"))
            answer = app.react_agent.run(
                text,
                on_step=lambda s: app._gui(lambda m=s: app.gui.set_status(m)))
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
