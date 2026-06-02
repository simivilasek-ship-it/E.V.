"""
ChatPanel helpers — add_message, _render_message, export.
Tyto metody jsou určeny k mixování do JarvisGUI (app_window.py).
"""

import re
from datetime import datetime
import customtkinter as ctk

from gui.constants import BG3, BORDER, CYAN2, FG, FG2


def add_message(self, text: str, sender: str):
    is_user = (sender == "user")
    ts = datetime.now().strftime("%H:%M")

    row = ctk.CTkFrame(self._chat, fg_color="transparent", corner_radius=0)
    row.pack(fill="x", padx=10, pady=4)

    meta = ctk.CTkFrame(row, fg_color="transparent")
    meta.pack(fill="x")
    if is_user:
        ctk.CTkLabel(meta, text=f"🧑  {ts}",
                     font=("Courier New", 8), text_color=BORDER).pack(side="right")
    else:
        ctk.CTkLabel(meta, text=f"🤖  {ts}",
                     font=("Courier New", 8), text_color=BORDER).pack(side="left")

    bubble = ctk.CTkFrame(
        row,
        fg_color=BG3 if is_user else "#080f1e",
        border_color=CYAN2 if is_user else BORDER,
        border_width=1,
        corner_radius=10,
    )
    bubble.pack(
        anchor="e" if is_user else "w",
        padx=(60, 0) if is_user else (0, 60),
        pady=(2, 0),
    )

    _render_message(self, bubble, text, is_user)

    self.root.after(60, lambda: self._chat._parent_canvas.yview_moveto(1.0))


def _render_message(self, parent, text: str, is_user: bool):
    """Renderuje text s podporou kódových bloků a základního markdownu."""
    parts = re.split(r"(```[\s\S]*?```)", text)

    for part in parts:
        if part.startswith("```") and part.endswith("```"):
            code = re.sub(r"^```\w*\n?", "", part).rstrip("`").strip()
            lines = code.count("\n") + 1
            height = min(max(lines, 2), 15)

            code_box = ctk.CTkTextbox(
                parent,
                font=("Courier New", 11),
                fg_color="#050c18",
                text_color="#80d8ff",
                border_color="#1a3a5c",
                border_width=1,
                corner_radius=6,
                height=height * 18 + 16,
                wrap="none",
                state="normal",
            )
            code_box.pack(fill="x", padx=8, pady=(4, 4))
            code_box.insert("end", code)
            code_box.configure(state="disabled")
        else:
            if not part.strip():
                continue
            clean = re.sub(r"\*\*(.+?)\*\*", r"\1", part)
            clean = re.sub(r"\*(.+?)\*", r"\1", clean)
            clean = re.sub(r"`([^`]+)`", r"[\1]", clean)
            clean = clean.strip()
            if clean:
                ctk.CTkLabel(
                    parent, text=clean,
                    font=("DM Sans", 12),
                    text_color=FG if is_user else FG2,
                    wraplength=310,
                    justify="right" if is_user else "left",
                    anchor="e" if is_user else "w",
                ).pack(padx=12, pady=(6, 6))


def export_chat(self):
    """Exportuje konverzaci do .md souboru na plochu."""
    from pathlib import Path

    lines = []
    for w in self._chat.winfo_children():
        for lbl in w.winfo_children():
            for sub in lbl.winfo_children():
                try:
                    t = sub.cget("text")
                    if t:
                        lines.append(t)
                except Exception:
                    pass

    if not lines:
        self._add_sys("Nic k exportu.")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = Path.home() / "Plocha" / f"jarvis_chat_{ts}.md"
    if not out.parent.exists():
        out = Path.home() / f"jarvis_chat_{ts}.md"

    out.write_text("# JARVIS chat export\n\n" + "\n\n".join(lines),
                   encoding="utf-8")
    self._add_sys(f"Exportováno: {out.name}")
