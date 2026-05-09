import logging
from typing import Any, Dict, Optional

try:
    import tkinter.messagebox as messagebox
except Exception:
    messagebox = None

logger = logging.getLogger(__name__)

ALLOWED_ACTIONS = {
    "open_app", "youtube_play", "open_url", "search_web", "write_text",
    "type_key", "kill_process", "weather", "vscode_open", "open_file",
    "create_folder", "create_file", "delete_file", "move_file", "find_files",
    "clipboard_set", "system_info", "get_time", "get_date", "set_timer",
    "write_email", "shutdown", "restart", "sleep_pc", "update_system",
    "screenshot", "volume", "media", "set_brightness", "install_app",
    "uninstall_app", "run_script", "calculate", "translate", "note_add",
    "note_list", "reminder_set", "wiki_search", "currency_convert",
    "memory_recall", "memory_store", "memory_stats", "memory_maintenance",
}

SENSITIVE_ACTIONS = {
    "delete_file", "shutdown", "restart", "sleep_pc", "update_system",
    "install_app", "uninstall_app", "run_script", "kill_process",
}


def is_action_allowed(action: str) -> bool:
    return action in ALLOWED_ACTIONS


def requires_confirmation(action: str, params: Dict[str, Any]) -> bool:
    return action in SENSITIVE_ACTIONS


def confirm_action(action: str, params: Dict[str, Any], parent: Optional[Any] = None) -> bool:
    if not requires_confirmation(action, params):
        return True

    prompt = f"Opravdu chcete provést akci '{action}'?"
    if params:
        details = ", ".join(f"{k}={v}" for k, v in params.items())
        prompt += f"\n{details}"

    logger.info(f"Žádost o potvrzení akce: {action} {params}")

    if messagebox:
        try:
            return messagebox.askyesno("Potvrzení akce", prompt, parent=parent)
        except Exception as e:
            logger.warning(f"Dialog potvrzení selhal: {e}")

    # Fallback: pokud není dostupný GUI dialog, akce neprojde.
    logger.warning("GUI potvrzení není dostupné, akce je zamítnuta.")
    return False
