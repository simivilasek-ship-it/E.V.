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


def cmd_release(argv: list[str] | None = None) -> int:
    """Interactive release assistant — bump version, draft changelog, create checklist."""
    import subprocess
    import re
    from pathlib import Path
    from datetime import date

    parser = argparse.ArgumentParser(prog="jarvis release", description="Release assistant")
    parser.add_argument("--bump", choices=["patch", "minor", "major"], default="patch")
    parser.add_argument("--dry-run", action="store_true", help="Only show what would happen")
    args = parser.parse_args(argv)

    root = Path(__file__).parent
    config_path = root / "config.py"

    # Read current version
    src = config_path.read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([\d.]+)"', src)
    if not m:
        print("Could not find __version__ in config.py")
        return 1

    current = m.group(1)
    parts = [int(x) for x in current.split(".")]
    while len(parts) < 3:
        parts.append(0)

    if args.bump == "patch":
        parts[2] += 1
    elif args.bump == "minor":
        parts[1] += 1
        parts[2] = 0
    elif args.bump == "major":
        parts[0] += 1
        parts[1] = 0
        parts[2] = 0

    next_ver = ".".join(str(p) for p in parts)
    today = date.today().isoformat()

    print(f"Current: {current}  →  Next: {next_ver}")

    # Collect recent git commits for changelog draft
    try:
        log = subprocess.check_output(
            ["git", "log", f"v{current}..HEAD", "--oneline", "--no-decorate"],
            cwd=root, text=True, stderr=subprocess.DEVNULL, timeout=5,
        ).strip()
    except Exception:
        log = ""

    changelog_entry = f"""
## [{next_ver}] - {today}

### Added / Changed
"""
    if log:
        for line in log.splitlines()[:20]:
            changelog_entry += f"- {line}\n"
    else:
        changelog_entry += "- (no commits found since last tag)\n"

    print("\n--- Changelog draft ---")
    print(changelog_entry)

    checklist = [
        f"[ ] Bump version in config.py: {current} → {next_ver}",
        f"[ ] Bump version in pyproject.toml",
        f"[ ] Bump version in Dockerfile / docker-compose.yml",
        f"[ ] Update CHANGELOG.md",
        f"[ ] Run: pytest tests/ test_jarvis.py -q",
        f"[ ] Run: cd web && npm run build",
        f"[ ] git tag -a v{next_ver} -m 'JARVIS v{next_ver}'",
        f"[ ] git push origin main && git push origin v{next_ver}",
    ]

    print("\n--- Release checklist ---")
    for item in checklist:
        print(item)

    if args.dry_run:
        print("\n[dry-run] No files changed.")
        return 0

    # Apply version bump
    new_src = re.sub(
        r'(__version__\s*=\s*)"[\d.]+"',
        f'\\1"{next_ver}"',
        src,
    )
    config_path.write_text(new_src, encoding="utf-8")
    print(f"\n✓ config.py bumped to {next_ver}")

    # Prepend changelog entry
    cl_path = root / "CHANGELOG.md"
    if cl_path.exists():
        existing = cl_path.read_text(encoding="utf-8")
        marker = "# CHANGELOG\n"
        if marker in existing:
            updated = existing.replace(marker, marker + "\n" + changelog_entry, 1)
            cl_path.write_text(updated, encoding="utf-8")
            print(f"✓ CHANGELOG.md updated")

    print(f"\nNext: run the checklist above to complete release v{next_ver}")
    return 0
