"""E.V. CLI subcommands — `jarvis log --today`."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date


_COMMANDS: dict[str, str] = {
    "log":      "cmd_log",
    "release":  "cmd_release",
    "briefing": "cmd_briefing",
}


def main(argv: list[str] | None = None) -> int:
    """Entry point: `jarvis <command> [args…]`"""
    if argv is None:
        argv = sys.argv[1:]

    if not argv or argv[0] in ("-h", "--help"):
        print("Použití: jarvis <příkaz> [volby]")
        print()
        print("Příkazy:")
        print("  log        Dnešní pracovní přehled z Work Timeline")
        print("  release    Asistent pro vydání nové verze")
        print("  briefing   Odeslat ranní přehled ihned (nebo naplánovat)")
        return 0

    cmd = argv[0]
    rest = argv[1:]

    fn_name = _COMMANDS.get(cmd)
    if fn_name is None:
        print(f"Neznámý příkaz: {cmd!r}")
        print(f"Dostupné příkazy: {', '.join(_COMMANDS)}")
        return 1

    fn = globals()[fn_name]
    return fn(rest)


if __name__ == "__main__":
    sys.exit(main())


def _format_summary_markdown(data: dict) -> str:
    lines = [f"# E.V. — přehled {data.get('date', date.today().isoformat())}", ""]
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


def cmd_briefing(argv: list[str] | None = None) -> int:
    """Send the E.V. morning briefing immediately."""
    import argparse

    parser = argparse.ArgumentParser(prog="jarvis briefing", description="E.V. ranní přehled")
    parser.add_argument(
        "--schedule",
        metavar="HH:MM",
        default=None,
        help="Naplánovat denní briefing na daný čas (např. 08:00)",
    )
    args = parser.parse_args(argv)

    if args.schedule:
        try:
            hour, minute = (int(x) for x in args.schedule.split(":"))
        except ValueError:
            print(f"Chybný formát času: {args.schedule!r} (očekáváno HH:MM)")
            return 1
        from morning_briefing import schedule_briefing
        schedule_briefing(hour=hour, minute=minute)
        print(f"Briefing naplánován na {hour:02d}:{minute:02d}.")
    else:
        from morning_briefing import send_briefing
        text = send_briefing()
        print(text)

    return 0


def cmd_release(argv: list[str] | None = None) -> int:
    """Single-source release assistant — bumps ALL version references across the project."""
    import subprocess
    import re
    from pathlib import Path
    from datetime import date

    parser = argparse.ArgumentParser(prog="jarvis release", description="E.V. release assistant")
    parser.add_argument("--bump", choices=["patch", "minor", "major"], default="patch")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change, don't write")
    parser.add_argument("--push", action="store_true", help="git tag + push after release")
    args = parser.parse_args(argv)

    root = Path(__file__).parent

    # ── Read current version ──────────────────────────────────────────────────
    config_path = root / "config.py"
    src = config_path.read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([\d.]+)"', src)
    if not m:
        print("ERROR: __version__ not found in config.py")
        return 1

    current = m.group(1)
    parts = [int(x) for x in current.split(".")]
    while len(parts) < 3:
        parts.append(0)

    if args.bump == "patch":
        parts[2] += 1
    elif args.bump == "minor":
        parts[1] += 1; parts[2] = 0
    elif args.bump == "major":
        parts[0] += 1; parts[1] = 0; parts[2] = 0

    nv = ".".join(str(p) for p in parts)
    today = date.today().isoformat()

    print(f"  {current}  →  {nv}")
    print()

    # ── Define all files + replacement strategies ─────────────────────────────
    def _bump_regex(path: Path, pattern: str, replacement: str, label: str):
        if not path.exists():
            print(f"  SKIP (not found): {path}")
            return
        src = path.read_text(encoding="utf-8")
        new = re.sub(pattern, replacement, src)
        if new == src:
            print(f"  ~ unchanged: {label}")
        else:
            if not args.dry_run:
                path.write_text(new, encoding="utf-8")
            print(f"  ✓ {'(dry) ' if args.dry_run else ''}updated: {label}")

    def _bump_str(path: Path, old: str, new_str: str, label: str):
        if not path.exists():
            print(f"  SKIP (not found): {path}")
            return
        src = path.read_text(encoding="utf-8")
        new = src.replace(old, new_str)
        if new == src:
            print(f"  ~ unchanged: {label}")
        else:
            if not args.dry_run:
                path.write_text(new, encoding="utf-8")
            print(f"  ✓ {'(dry) ' if args.dry_run else ''}updated: {label}")

    print("── Version bumps ────────────────────────────────────────────")
    # config.py
    _bump_regex(root / "config.py",
        r'(__version__\s*=\s*)"[\d.]+"', f'\\g<1>"{nv}"', "config.py __version__")

    # pyproject.toml
    _bump_regex(root / "pyproject.toml",
        r'^(version\s*=\s*)"[\d.]+"', f'\\g<1>"{nv}"', "pyproject.toml version",)

    # Dockerfile + docker-compose.yml + requirements.txt — comment version strings
    for fname in ["Dockerfile", "docker-compose.yml", "requirements.txt"]:
        p = root / fname
        src2 = p.read_text(encoding="utf-8") if p.exists() else ""
        new2 = src2.replace(f"v{current}", f"v{nv}").replace(current, nv)
        if new2 != src2:
            if not args.dry_run:
                p.write_text(new2, encoding="utf-8")
            print(f"  ✓ {'(dry) ' if args.dry_run else ''}updated: {fname}")
        else:
            print(f"  ~ unchanged: {fname}")

    # README.md — badges + version mentions
    readme = root / "README.md"
    if readme.exists():
        src3 = readme.read_text(encoding="utf-8")
        short_cur = ".".join(current.split(".")[:2])
        short_nv  = ".".join(nv.split(".")[:2])
        new3 = (src3
            .replace(f"v{current}", f"v{nv}")
            .replace(current, nv)
            .replace(f"v{short_cur}", f"v{short_nv}")
        )
        if new3 != src3:
            if not args.dry_run:
                readme.write_text(new3, encoding="utf-8")
            print(f"  ✓ {'(dry) ' if args.dry_run else ''}updated: README.md")
        else:
            print(f"  ~ unchanged: README.md")

    # web/components/Sidebar.tsx
    sidebar = root / "web" / "components" / "Sidebar.tsx"
    if sidebar.exists():
        src4 = sidebar.read_text(encoding="utf-8")
        short_cur = ".".join(current.split(".")[:2])
        short_nv  = ".".join(nv.split(".")[:2])
        new4 = src4.replace(f"v{short_cur}", f"v{short_nv}").replace(f"v{current}", f"v{nv}")
        if new4 != src4:
            if not args.dry_run:
                sidebar.write_text(new4, encoding="utf-8")
            print(f"  ✓ {'(dry) ' if args.dry_run else ''}updated: web/components/Sidebar.tsx")
        else:
            print(f"  ~ unchanged: Sidebar.tsx")

    # docs/*.md
    for doc in (root / "docs").glob("*.md"):
        src5 = doc.read_text(encoding="utf-8")
        new5 = src5.replace(f"v{current}", f"v{nv}").replace(current, nv)
        if new5 != src5:
            if not args.dry_run:
                doc.write_text(new5, encoding="utf-8")
            print(f"  ✓ {'(dry) ' if args.dry_run else ''}updated: docs/{doc.name}")

    # ── Changelog entry ───────────────────────────────────────────────────────
    print()
    print("── Changelog draft ──────────────────────────────────────────")
    try:
        log = subprocess.check_output(
            ["git", "log", f"v{current}..HEAD", "--oneline", "--no-decorate"],
            cwd=root, text=True, stderr=subprocess.DEVNULL, timeout=5,
        ).strip()
    except Exception:
        log = ""

    changelog_entry = f"## [{nv}] - {today}\n\n### Added / Changed\n"
    if log:
        for line in log.splitlines()[:20]:
            changelog_entry += f"- {line}\n"
    else:
        changelog_entry += "- (no new commits since last tag)\n"
    changelog_entry += "\n"

    print(changelog_entry)

    cl_path = root / "CHANGELOG.md"
    if cl_path.exists() and not args.dry_run:
        existing = cl_path.read_text(encoding="utf-8")
        marker = "# CHANGELOG\n"
        if marker in existing:
            cl_path.write_text(existing.replace(marker, marker + "\n" + changelog_entry, 1), encoding="utf-8")
        else:
            cl_path.write_text(changelog_entry + existing, encoding="utf-8")
        print(f"  ✓ CHANGELOG.md prepended")

    # ── Release checklist ─────────────────────────────────────────────────────
    print()
    print("── Release checklist ────────────────────────────────────────")
    checks = [
        f"[x] config.py → {nv}",
        f"[x] pyproject.toml → {nv}",
        f"[x] Dockerfile / docker-compose.yml → v{nv}",
        f"[x] README.md badges → v{nv}",
        f"[x] CHANGELOG.md updated",
        "[ ] pytest tests/ test_jarvis.py -q",
        "[ ] cd web && npm run build",
        f"[ ] git tag -a v{nv} -m 'E.V. v{nv}'",
        f"[ ] git push origin main && git push origin v{nv}",
    ]
    for c in checks:
        print(f"  {c}")

    if args.dry_run:
        print("\n[dry-run] No files written.")
        return 0

    # ── Optional git tag + push ───────────────────────────────────────────────
    if args.push:
        print()
        print("── Git tag + push ───────────────────────────────────────────")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"chore: bump version to {nv}"],
            cwd=root, check=True,
        )
        subprocess.run(["git", "tag", "-a", f"v{nv}", "-m", f"E.V. v{nv}"], cwd=root, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=root, check=True)
        subprocess.run(["git", "push", "origin", f"v{nv}"], cwd=root, check=True)
        print(f"  ✓ Pushed v{nv}")

    print(f"\n✓ Release v{nv} prepared. Run tests, then: git tag -a v{nv} -m 'E.V. v{nv}' && git push origin main v{nv}")
    return 0


def cmd_config_validate(argv: list[str] | None = None) -> int:
    """Validate E.V. config.json with the Pydantic schema."""
    import argparse
    import json
    import os
    from pathlib import Path

    parser = argparse.ArgumentParser(
        prog="jarvis config validate",
        description="Validate E.V. config.json against the Pydantic schema.",
    )
    parser.add_argument(
        "--path", type=str, default="",
        help="Path to config.json (default: ~/.config/jarvis/config.json or ./config.json)",
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args(argv)

    # Resolve config path
    if args.path:
        config_path = Path(args.path)
    else:
        xdg = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        candidates = [xdg / "jarvis" / "config.json", Path("config.json")]
        config_path = next((p for p in candidates if p.exists()), Path("config.json"))

    if not config_path.exists():
        msg = f"Config file not found: {config_path}"
        if args.json:
            print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
        else:
            print(f"ERROR: {msg}")
        return 1

    try:
        with open(config_path, encoding="utf-8") as f:
            cfg = json.load(f)
    except json.JSONDecodeError as e:
        msg = f"Invalid JSON: {e}"
        if args.json:
            print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
        else:
            print(f"ERROR: {msg}")
        return 1

    from src.config_schema import validate_config
    settings, warns = validate_config(cfg)

    if args.json:
        print(json.dumps({
            "ok": True,
            "config_path": str(config_path),
            "warnings": warns,
            "ollama_model": settings.ollama_model,
            "history_size": settings.history_size,
        }, ensure_ascii=False, indent=2))
        return 0

    print(f"Config: {config_path}")
    if warns:
        print(f"WARNINGS ({len(warns)}):")
        for w in warns:
            print(f"  ⚠  {w}")
        return 0

    print(f"OK — model={settings.ollama_model}, history={settings.history_size}")
    return 0
