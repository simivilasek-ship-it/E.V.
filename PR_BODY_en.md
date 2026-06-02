Title: feat: proactive context-aware triggers + nightly reports; security hardening for headless

Short description:
This PR introduces a ProactiveEngine that listens for active-window changes and generates contextual suggestions when the user opens a code file in VS Code (scans TODO/FIXME, recent failing tests, git summary). It also adds a daily markdown report generator that saves per-day summaries to ~/jarvis_reports/YYYY-MM-DD.md.

Security change:
- Headless mode no longer auto-approves ELEVATED actions (e.g. delete_file, shutdown). To opt-in for controlled/dev environments, set environment variable JARVIS_HEADLESS_APPROVE_ELEVATED=1. This change reduces the risk of unintended critical actions on headless deployments.

Files added/modified:
- Added: proactive.py (new module)
- Modified: app_core.py (integrate ProactiveEngine), security_v2.py (confirm_action behavior), README.md, CHANGELOG.md
- Tests added: tests/test_confirm_action_headless.py, tests/test_proactive.py

Config:
- New config keys (optional):
  - proactive.enabled (default true)
  - proactive_daily_time (default "18:00")
  - proactive_workspace_roots (list of paths to search for files)

Testing:
- Unit tests were added for headless confirmation behavior and proactive scanning/report generation. Run full test suite with pytest.

Notes:
- Proactive engine reads local files and runs git subprocesses; ensure appropriate permissions and avoid enabling on shared/public servers if sensitive.
- Daily reports are stored under ~/jarvis_reports. Consider retention/rotation if needed.

Suggested reviewers: security, core, notification
Labels: enhancement, security, tests
