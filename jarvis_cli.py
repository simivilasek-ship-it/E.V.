"""JARVIS CLI subcommands — `jarvis log --today`."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date


def _format_summary_markdown(data: dict) -> str:
    lines = [f"# JARVIS — přehled {data.get('date', date.today().isoformat())}", ""]
    for item in data.get("summary") or []:
        lines.append(f"- {item}")
    if not data.get("summary"):
        lines.append("- Žádná zaznamenaná aktivita.")
    projects = data.get("projects") or {}
    if projects:
        lines.extend(["", "## Projekty", ""])
        for name, hours in sorted(projects.items(), key=lambda x: -x[1]):
            lines.append(f"- **{name}** — {hours} h")
    apps = data.get("apps") or []
    if apps:
        lines.extend(["", "## Aplikace", "", ", ".join(apps)])
    bugs = data.get("bugs") or []
    if bugs:
        lines.extend(["", "## Problémy / buildy", ""])
        for b in bugs[:5]:
            lines.append(f"- {b.get('title', '?')}: {b.get('detail', '')[:80]}")
    lines.append("")
    lines.append(f"*Událostí: {data.get('events_count', 0)}*")
    return "\n".join(lines)


def cmd_log(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jarvis log", description="Work Timeline log")
    parser.add_argument("--today", action="store_true", help="Dnešní přehled (výchozí)")
    parser.add_argument("--day", type=str, default="", help="Datum YYYY-MM-DD")
    parser.add_argument("--json", action="store_true", help="Výstup jako JSON")
    parser.add_argument("--markdown", action="store_true", help="Výstup jako Markdown")
    args = parser.parse_args(argv)

    from activity_store import get_activity_store

    d = date.fromisoformat(args.day) if args.day else None
    data = get_activity_store().daily_summary(d)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif args.markdown:
        print(_format_summary_markdown(data))
    else:
        print(data.get("summary_text", "Žádná aktivita."))
        if data.get("projects"):
            print("\nProjekty:")
            for name, hours in sorted(data["projects"].items(), key=lambda x: -x[1]):
                print(f"  {name}: {hours} h")
    return 0
