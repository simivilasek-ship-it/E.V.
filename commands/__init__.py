"""
JARVIS commands package.
CommandExecutor deleguje na podmoduly: system, apps, media, files, utils.
"""

import logging
from typing import Any, Dict, Optional

from .apps   import (APP_MAP, find_app, cmd_open_app, cmd_kill_process,
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
                     cmd_shutdown, cmd_restart, cmd_sleep_pc,
                     cmd_update_system, cmd_volume, cmd_set_brightness)
from .utils  import (cmd_calculate, cmd_translate, cmd_note_add, cmd_note_list,
                     cmd_reminder_set, cmd_weather, cmd_wiki_search,
                     cmd_currency_convert, cmd_write_email,
                     cmd_memory_recall, cmd_memory_store,
                     cmd_memory_stats, cmd_memory_maintenance)

logger = logging.getLogger(__name__)

__all__ = ["CommandExecutor", "APP_MAP"]


class CommandExecutor:
    """Facade — deleguje volání na podmoduly."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    def execute(self, action: str, params: Dict[str, Any]) -> str:
        try:
            method = getattr(self, f"_cmd_{action}", None)
            if method is None:
                logger.warning(f"Neznámá akce: {action}")
                return f"Neznámá akce: {action}"
            return method(**params)
        except Exception as e:
            logger.exception(f"Chyba při vykonávání {action}")
            return f"Chyba: {e}"

    # ── system ───────────────────────────────────────
    def _cmd_get_time(self, **_):             return cmd_get_time()
    def _cmd_get_date(self, **_):             return cmd_get_date()
    def _cmd_system_info(self, **_):          return cmd_system_info()
    def _cmd_shutdown(self, delay=0, **_):    return cmd_shutdown(delay)
    def _cmd_restart(self, delay=0, **_):     return cmd_restart(delay)
    def _cmd_sleep_pc(self, **_):             return cmd_sleep_pc()
    def _cmd_update_system(self, **_):        return cmd_update_system()
    def _cmd_volume(self, level=None, action=None, **_):
        return cmd_volume(level=level, action=action)
    def _cmd_set_brightness(self, level=50, **_): return cmd_set_brightness(level)

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

    # ── no-ops ───────────────────────────────────────
    def _cmd_answer(self, **_):                     return "ok"
    def _cmd_clear_history(self, **_):              return "ok"
