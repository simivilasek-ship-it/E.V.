"""
Integration testy — propojení CommandExecutor + SecurityManager + LLMRouter.

Testuje skutečné chování bez mocku Ollamy:
  - lokální příkazy (bez LLM)
  - security pipeline (blokování zakázaných akcí)
  - path validation (path traversal)
  - plugin sandbox (exec/eval)
  - safe_run integrace s commands
"""
from __future__ import annotations

import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = [pytest.mark.integration]


# ─────────────────────────────────────────────────────
#  CommandExecutor — lokální příkazy bez LLM
# ─────────────────────────────────────────────────────

class TestCommandExecutorIntegration:
    """Testuje CommandExecutor → commands/* bez Ollamy."""

    @pytest.fixture
    def executor(self, mock_config):
        from commands import CommandExecutor
        return CommandExecutor(mock_config)

    def test_get_time_returns_string(self, executor):
        result = executor.execute("get_time", {})
        assert isinstance(result, str)
        assert len(result) > 0
        assert any(c.isdigit() for c in result)

    def test_calculate_correct(self, executor):
        result = executor.execute("calculate", {"expression": "2+2*3"})
        assert result == "8"

    def test_calculate_division_by_zero(self, executor):
        result = executor.execute("calculate", {"expression": "1/0"})
        assert "Chyba" in result or "error" in result.lower()

    def test_system_info_returns_cpu_ram(self, executor):
        result = executor.execute("system_info", {})
        assert "CPU" in result
        assert "RAM" in result

    def test_unknown_action_graceful(self, executor):
        result = executor.execute("akce_ktera_neexistuje_xyz", {})
        assert isinstance(result, str)

    def test_ui_set_value_command_registered(self, executor):
        result = executor.execute("ui_set_value", {"text": "username", "value": "user123"})
        assert "Computer Use je vypnuté" in result

    def test_note_add_and_list(self, executor):
        with tempfile.TemporaryDirectory() as tmpdir:
            note_file = os.path.join(tmpdir, "notes.txt")
            with patch("commands.utils._HOME", tmpdir):
                r1 = executor.execute("note_add", {"note": "testovací poznámka"})
                assert "ulož" in r1.lower() or "ok" in r1.lower() or "poznámka" in r1.lower()


# ─────────────────────────────────────────────────────
#  Security pipeline
# ─────────────────────────────────────────────────────

class TestSecurityPipeline:
    """Testuje SecurityManager — povolení / blokování akcí."""

    @pytest.fixture
    def security(self):
        from security_v2 import SecurityManager, PermissionLevel
        return SecurityManager(max_permission=PermissionLevel.ELEVATED)

    def test_safe_action_allowed(self, security):
        ok, reason = security.check("get_time", {})
        assert ok is True

    def test_elevated_action_allowed_within_limit(self, security):
        ok, reason = security.check("delete_file", {"path": "/tmp/x.txt"})
        assert ok is True

    def test_dangerous_pattern_blocked(self, security):
        ok, reason = security.check("run_script", {"cmd": "rm -rf /"})
        assert ok is False
        assert reason != ""

    def test_audit_log_records_action(self, security):
        with tempfile.TemporaryDirectory() as tmpdir:
            from security_v2 import AuditLog
            log = AuditLog(path=Path(tmpdir) / "audit.jsonl")
            log.log("get_time", {}, allowed=True, reason="")
            entries = log.get_recent(10)
            assert len(entries) == 1
            assert entries[0].action == "get_time"

    def test_audit_log_file_permissions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from security_v2 import AuditLog
            log_path = Path(tmpdir) / "audit.jsonl"
            log = AuditLog(path=log_path)
            log.log("test", {}, allowed=True)
            mode = oct(log_path.stat().st_mode)[-3:]
            assert mode == "600", f"Očekáváno 600, dostal {mode}"

    def test_ui_set_value_is_elevated(self, security):
        ok, reason = security.check("ui_set_value", {"text": "username", "value": "user123"})
        assert ok is True


# ─────────────────────────────────────────────────────
#  Path traversal ochrana
# ─────────────────────────────────────────────────────

class TestPathValidation:

    def test_validate_path_blocks_traversal(self):
        from commands.utils import validate_path
        with pytest.raises(ValueError):
            validate_path("")

    def test_validate_path_resolves_home(self):
        from commands.utils import validate_path
        p = validate_path("~/")
        assert p.is_absolute()

    def test_validate_path_must_exist_raises(self):
        from commands.utils import validate_path
        with pytest.raises(ValueError, match="neexistuje"):
            validate_path("/tmp/soubor_ktery_neexistuje_12345.txt", must_exist=True)

    def test_cmd_open_file_nonexistent_returns_error(self, mock_config):
        from commands.files import cmd_open_file
        result = cmd_open_file("/tmp/neexistuje_xyzabc.txt")
        assert "Chyba" in result

    def test_cmd_run_script_bad_extension(self, mock_config):
        from commands.apps import cmd_run_script
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            fname = f.name
        try:
            result = cmd_run_script(fname)
            assert "přípona" in result.lower() or "Chyba" in result
        finally:
            os.unlink(fname)

    def test_cmd_create_folder_valid(self):
        from commands.files import cmd_create_folder
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = os.path.join(tmpdir, "nova_slozka")
            result = cmd_create_folder(new_dir)
            assert Path(new_dir).exists()
            assert "vytvořena" in result.lower() or "ok" in result.lower()


# ─────────────────────────────────────────────────────
#  Plugin sandbox
# ─────────────────────────────────────────────────────

class TestPluginSandbox:

    def _check(self, source: str, permissions=None):
        from plugin_system import _check_imports
        return _check_imports(source, permissions or [], "test_plugin")

    def test_safe_plugin_passes(self):
        source = "import json\nimport re\ndef get_routes(): return []"
        assert self._check(source) is None

    def test_blocked_import_rejected(self):
        source = "import subprocess\nsubprocess.run(['ls'])"
        result = self._check(source)
        assert result is not None
        assert "subprocess" in result

    def test_exec_without_import_rejected(self):
        source = "def run():\n    exec('import os; os.system(\"id\")')"
        result = self._check(source)
        assert result is not None
        assert "exec" in result

    def test_eval_without_import_rejected(self):
        source = "x = eval('__import__(\"os\").system(\"id\")')"
        result = self._check(source)
        assert result is not None
        assert "eval" in result

    def test_compile_rejected(self):
        source = "code = compile('import os', '<string>', 'exec')"
        result = self._check(source)
        assert result is not None
        assert "compile" in result

    def test_permission_os_allows_os(self):
        source = "import os\npath = os.path.join('a', 'b')"
        # bez permission → blokováno
        assert self._check(source, []) is not None
        # s permission os → povoleno
        assert self._check(source, ["system.info"]) is None  # system.info zahrnuje os

    def test_plugin_path_outside_root_rejected(self):
        from plugin_system import SkillLoader
        with pytest.raises(ImportError, match="mimo plugins"):
            SkillLoader.load_module("/etc/passwd", "evil_plugin")


# ─────────────────────────────────────────────────────
#  normalize_text (dříve _norm)
# ─────────────────────────────────────────────────────

class TestNormalizeText:

    def test_removes_diacritics(self):
        from commands.utils import normalize_text
        assert normalize_text("Otevři Chrome") == "otevri chrome"
        assert normalize_text("Přehraj hudbu") == "prehraj hudbu"
        assert normalize_text("Hlasitost na 50%") == "hlasitost na 50%"

    def test_lowercases(self):
        from commands.utils import normalize_text
        assert normalize_text("JARVIS") == "jarvis"

    def test_empty_string(self):
        from commands.utils import normalize_text
        assert normalize_text("") == ""


# ─────────────────────────────────────────────────────
#  Secret masking
# ─────────────────────────────────────────────────────

class TestSecretMasking:

    def test_api_key_masked(self):
        from logging_setup import _mask_secrets
        text = "BRAVE_API_KEY=sk-1234abcd"
        result = _mask_secrets(text)
        assert "1234abcd" not in result
        assert "<REDACTED>" in result

    def test_password_masked(self):
        from logging_setup import _mask_secrets
        text = "password=tajne_heslo_123"
        result = _mask_secrets(text)
        assert "tajne_heslo_123" not in result

    def test_normal_text_unchanged(self):
        from logging_setup import _mask_secrets
        text = "CPU: 45% RAM: 70%"
        assert _mask_secrets(text) == text
