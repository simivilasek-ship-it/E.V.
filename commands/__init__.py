"""
JARVIS commands package.
CommandExecutor deleguje na podmoduly: system, apps, media, files, utils.
"""

import logging
import os
import shutil
from collections import deque
from typing import Any, Dict, List

from .apps   import (APP_MAP, find_app, cmd_open_app, cmd_kill_process,  # noqa: F401
                     cmd_install_app, cmd_uninstall_app, cmd_run_script,
                     cmd_vscode_open)
from .files  import (cmd_open_url, cmd_search_web, cmd_open_file,
                     cmd_create_folder, cmd_create_file, cmd_delete_file,
                     cmd_move_file, cmd_find_files, cmd_clipboard_set)
from .media  import (cmd_screenshot, cmd_type_key, cmd_write_text, cmd_media,
                     cmd_set_timer, cmd_youtube_play, cmd_youtube_download,
                     cmd_youtube_info, cmd_youtube_subtitles,
                     cmd_screen_describe, cmd_screen_ocr, cmd_webcam_describe)
from .system import (cmd_get_time, cmd_get_date, cmd_system_info,
                     cmd_pc_overview,
                     cmd_shutdown, cmd_restart, cmd_sleep_pc,
                     cmd_update_system, cmd_volume, cmd_set_brightness,
                     cmd_hardware_info, cmd_disk_space,
                     cmd_list_directory, cmd_file_info)
from .ui_automation import (cmd_ui_tree, cmd_ui_click, cmd_ui_set_value)
from shadow_mode import cmd_shadow_suggest
from mcp_hub import cmd_mcp_suggest
from .utils  import (cmd_calculate, cmd_translate, cmd_note_add, cmd_note_list,
                     cmd_reminder_set, cmd_weather, cmd_wiki_search,
                     cmd_currency_convert, cmd_write_email,
                     cmd_memory_recall, cmd_memory_store,
                     cmd_memory_stats, cmd_memory_maintenance,
                     cmd_sports)

logger = logging.getLogger(__name__)

__all__ = ["CommandExecutor", "APP_MAP", "find_app"]


# Akce, pro které ukládáme snapshot před provedením
_UNDOABLE = {"create_folder", "create_file", "delete_file", "move_file", "clipboard_set"}


class UndoEntry:
    __slots__ = ("action", "params", "snapshot")
    def __init__(self, action: str, params: dict, snapshot: dict):
        self.action = action
        self.params = params
        self.snapshot = snapshot


class CommandExecutor:
    """Facade — deleguje volání na podmoduly.

    Udržuje undo stack (max 20 kroků) pro souborové a schránkové operace.
    executor.undo() nebo příkaz „vrať poslední akci".
    """

    _UNDO_LIMIT = 20

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config      = config
        self._undo_stack: deque = deque(maxlen=self._UNDO_LIMIT)

    def execute(self, action: str, params: Dict[str, Any]) -> str:
        # Validace: action musí být slug (jen písmena, číslice, podtržítko)
        # Zabrání volání privátních metod jako _shutdown nebo __init__
        import re as _re
        if not _re.match(r'^[a-z][a-z0-9_]*$', action):
            logger.warning(f"Neplatná akce (odmítnuto): {action!r}")
            return f"Neplatná akce: {action}"
        try:
            method = getattr(self, f"_cmd_{action}", None)
            if method is None:
                logger.warning(f"Neznámá akce: {action}")
                return f"Neznámá akce: {action}"
            snap   = self._snapshot_before(action, params) if action in _UNDOABLE else None
            result = method(**params)
            if snap is not None:
                self._undo_stack.append(UndoEntry(action, params, snap))
            return result
        except Exception as e:
            logger.exception(f"Chyba při vykonávání {action}")
            return f"Chyba: {e}"

    def undo(self) -> str:
        if not self._undo_stack:
            return "Nic k vrácení."
        try:
            return self._apply_undo(self._undo_stack.pop())
        except Exception as e:
            return f"Undo selhalo: {e}"

    def undo_history(self) -> List[str]:
        return [f"{e.action}({e.params})" for e in reversed(self._undo_stack)]

    def _snapshot_before(self, action: str, params: dict) -> dict:
        snap: dict = {}
        try:
            if action == "create_folder":
                p = params.get("path", "")
                snap = {"path": p, "existed": os.path.isdir(p)}
            elif action == "create_file":
                p = params.get("path", "")
                snap = {"path": p, "existed": os.path.isfile(p)}
                if snap["existed"]:
                    snap["content"] = open(p, "rb").read()
            elif action == "delete_file":
                p = params.get("path", "")
                snap = {"path": p}
                if os.path.isfile(p):
                    snap["content"] = open(p, "rb").read()
                elif os.path.isdir(p):
                    snap["is_dir"] = True
            elif action == "move_file":
                snap = {"src": params.get("src", ""), "dst": params.get("dst", "")}
            elif action == "clipboard_set":
                try:
                    import pyperclip
                    snap["previous"] = pyperclip.paste()
                except Exception:
                    snap["previous"] = ""
        except Exception as e:
            logger.debug(f"Snapshot chyba: {e}")
        return snap

    def _apply_undo(self, entry: UndoEntry) -> str:
        a, snap = entry.action, entry.snapshot
        if a == "create_folder":
            p = snap.get("path", "")
            if not snap.get("existed") and os.path.isdir(p):
                shutil.rmtree(p)
                return f"Undo: složka {p} smazána."
        elif a == "create_file":
            p = snap.get("path", "")
            if not snap.get("existed") and os.path.isfile(p):
                os.remove(p)
                return f"Undo: soubor {p} smazán."
            elif "content" in snap:
                open(p, "wb").write(snap["content"])
                return f"Undo: soubor {p} obnoven."
        elif a == "delete_file":
            p = snap.get("path", "")
            if "content" in snap and not os.path.exists(p):
                open(p, "wb").write(snap["content"])
                return f"Undo: {p} obnoven."
        elif a == "move_file":
            src, dst = snap.get("src", ""), snap.get("dst", "")
            if dst and os.path.exists(dst):
                shutil.move(dst, src)
                return f"Undo: {dst} → {src}."
        elif a == "clipboard_set":
            try:
                import pyperclip
                pyperclip.copy(snap.get("previous", ""))
                return "Undo: schránka obnovena."
            except Exception:
                pass
        return f"Undo {a}: nelze vrátit (stav se změnil)."

    # ── system ───────────────────────────────────────
    def _cmd_get_time(self, **_):             return cmd_get_time()
    def _cmd_get_date(self, **_):             return cmd_get_date()
    def _cmd_system_info(self, **_):          return cmd_system_info()
    def _cmd_pc_overview(self, **_):          return cmd_pc_overview()
    def _cmd_shutdown(self, delay=0, **_):    return cmd_shutdown(delay)
    def _cmd_restart(self, delay=0, **_):     return cmd_restart(delay)
    def _cmd_sleep_pc(self, **_):             return cmd_sleep_pc()
    def _cmd_update_system(self, **_):        return cmd_update_system()
    def _cmd_volume(self, level=None, action=None, **_):
        return cmd_volume(level=level, action=action)
    def _cmd_set_brightness(self, level=50, **_): return cmd_set_brightness(level)
    def _cmd_hardware_info(self, **_):            return cmd_hardware_info()
    def _cmd_disk_space(self, path="/", **_):     return cmd_disk_space(path)
    def _cmd_list_directory(self, path="~", **_): return cmd_list_directory(path)
    def _cmd_file_info(self, path="", **_):       return cmd_file_info(path)
    def _cmd_ui_tree(self, max_nodes=400, **_):    return cmd_ui_tree(max_nodes=max_nodes)
    def _cmd_ui_click(self, text="", role="", **_): return cmd_ui_click(text=text, role=role)
    def _cmd_ui_set_value(self, text="", value="", role="", **_): return cmd_ui_set_value(text=text, value=value, role=role)
    def _cmd_shadow_suggest(self, **_):             return cmd_shadow_suggest(self.config)
    def _cmd_mcp_suggest(self, task="", **_):       return cmd_mcp_suggest(task)

    # ── apps ─────────────────────────────────────────
    def _cmd_open_app(self, app="", args=None, **_): return cmd_open_app(app, args)
    def _cmd_kill_process(self, name="", **_):       return cmd_kill_process(name)
    def _cmd_install_app(self, name="", **_):        return cmd_install_app(name)
    def _cmd_uninstall_app(self, name="", **_):      return cmd_uninstall_app(name)
    def _cmd_run_script(self, path="", **_):         return cmd_run_script(path)
    def _cmd_vscode_open(self, path="", **_):        return cmd_vscode_open(path)

    # ── files ────────────────────────────────────────
    def _cmd_open_url(self, url="", **_):            return cmd_open_url(url)
    def _cmd_search_web(self, query="", **_):        return cmd_search_web(query)
    def _cmd_open_file(self, path="", **_):          return cmd_open_file(path)
    def _cmd_create_folder(self, path="", **_):      return cmd_create_folder(path)
    def _cmd_create_file(self, path="", **_):        return cmd_create_file(path)
    def _cmd_delete_file(self, path="", **_):        return cmd_delete_file(path)
    def _cmd_move_file(self, src="", dst="", **_):   return cmd_move_file(src, dst)
    def _cmd_find_files(self, name="", path="~", **_): return cmd_find_files(name, path)
    def _cmd_clipboard_set(self, text="", **_):      return cmd_clipboard_set(text)

    # ── media ────────────────────────────────────────
    def _cmd_screenshot(self, **_):                  return cmd_screenshot()
    def _cmd_type_key(self, key="", **_):            return cmd_type_key(key)
    def _cmd_write_text(self, text="", **_):         return cmd_write_text(text)
    def _cmd_media(self, action=None, url=None, **_): return cmd_media(action, url)
    def _cmd_set_timer(self, seconds=60, label="Timer", **_):
        return cmd_set_timer(seconds, label)
    def _cmd_youtube_play(self, query="", index=1, audio_only=False, **_):
        return cmd_youtube_play(query, index, audio_only)
    def _cmd_youtube_download(self, query="", path="", audio_only=False, quality="best", **_):
        return cmd_youtube_download(query, path, audio_only, quality)
    def _cmd_youtube_info(self, query="", **_):      return cmd_youtube_info(query)
    def _cmd_youtube_subtitles(self, query="", lang="cs", path="", **_):
        return cmd_youtube_subtitles(query, lang, path)

    # ── utils ────────────────────────────────────────
    def _cmd_calculate(self, expression="", **_):   return cmd_calculate(expression)
    def _cmd_translate(self, text="", from_lang="auto", to_lang="cs", **_):
        return cmd_translate(text, from_lang, to_lang,
                             ollama_model=self.config.get("ollama_model", "qwen2.5:3b"),
                             ollama_url=self.config.get("ollama_url",
                                                        "http://localhost:11434/api/chat"))
    def _cmd_note_add(self, note="", **_):          return cmd_note_add(note)
    def _cmd_note_list(self, **_):                  return cmd_note_list()
    def _cmd_reminder_set(self, text="", time_str="1 minuta", **_):
        return cmd_reminder_set(text, time_str)
    def _cmd_weather(self, city="", **_):           return cmd_weather(city)
    def _cmd_wiki_search(self, query="", **_):      return cmd_wiki_search(query)
    def _cmd_currency_convert(self, amount=1.0, from_curr="USD", to_curr="CZK", **_):
        return cmd_currency_convert(amount, from_curr, to_curr)
    def _cmd_write_email(self, to="", subject="", body="", **_):
        return cmd_write_email(to, subject, body)
    def _cmd_memory_recall(self, query="", top_k=5, **_):
        return cmd_memory_recall(self.config, query, top_k)
    def _cmd_memory_store(self, content="", importance=0.5, **_):
        return cmd_memory_store(self.config, content, importance)
    def _cmd_memory_stats(self, **_):               return cmd_memory_stats(self.config)
    def _cmd_memory_maintenance(self, **_):         return cmd_memory_maintenance(self.config)

    # ── vision ───────────────────────────────────────
    def _cmd_screen_describe(self, **_):           return cmd_screen_describe()
    def _cmd_screen_ocr(self, **_):                return cmd_screen_ocr()
    def _cmd_webcam_describe(self, **_):           return cmd_webcam_describe()

    # ── sports ───────────────────────────────────────
    def _cmd_sports(self, query="", **_):            return cmd_sports(query)

    # ── parallel agents ───────────────────────────────
    def _cmd_agent_parallel_task(self, task="", max_steps=5, **_):
        try:
            from agent_roles import MultiAgentOrchestrator
            url   = self.config.get("ollama_url",   "http://localhost:11434/api/chat")
            model = self.config.get("ollama_model", "qwen2.5:3b")
            orch  = MultiAgentOrchestrator(url, model, executor=self)
            return orch.run_parallel(task, max_steps=int(max_steps))
        except Exception as e:
            return f"Paralelní agenti selhali: {e}"

    # ── undo ─────────────────────────────────────────
    def _cmd_undo(self, **_):                        return self.undo()
    def _cmd_undo_history(self, **_):                return "\n".join(self.undo_history()) or "Prázdná historie."

    # ── no-ops ───────────────────────────────────────
    def _cmd_answer(self, **_):                     return "ok"
    def _cmd_clear_history(self, **_):              return "ok"

