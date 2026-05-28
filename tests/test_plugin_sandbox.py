"""
B2 — Plugin API spec + sandboxing testy
"""
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugin_system import ManifestValidator, PluginManager


class TestManifestValidator:
    def test_valid_manifest(self):
        manifest = {
            "name": "test_plugin",
            "version": "1.0.0",
            "description": "Testovací plugin",
            "author": "Tester",
            "permissions": ["answer", "mcp"],
            "triggers": ["test"],
        }
        valid, err = ManifestValidator.validate(manifest)
        assert valid is True
        assert err == ""

    def test_missing_required_field(self):
        manifest = {
            "version": "1.0.0",
            "description": "Chybí name",
            "permissions": ["answer"],
        }
        valid, err = ManifestValidator.validate(manifest)
        assert valid is False
        assert "Chybí" in err
        assert "name" in err

    def test_invalid_permission(self):
        manifest = {
            "name": "hack_plugin",
            "version": "1.0.0",
            "description": "Pokus o hack",
            "permissions": ["hack"],
        }
        valid, err = ManifestValidator.validate(manifest)
        assert valid is False
        assert "Neplatné" in err
        assert "hack" in err

    def test_wrong_type(self):
        manifest = {
            "name": 123,
            "version": "1.0.0",
            "description": "Špatný typ name",
            "permissions": ["answer"],
        }
        valid, err = ManifestValidator.validate(manifest)
        assert valid is False
        assert "musí být" in err

    def test_optional_author_missing(self):
        """Starý manifest bez 'author' musí projít — zpětná kompatibilita."""
        manifest = {
            "name": "legacy_plugin",
            "version": "1.0.0",
            "description": "Starý plugin bez autora",
            "permissions": ["answer"],
        }
        valid, err = ManifestValidator.validate(manifest)
        assert valid is True
        assert err == ""


class TestPluginSandbox:
    def _make_manager(self) -> PluginManager:
        # Krátký timeout aby test nepřekročil pytest limit 5s
        return PluginManager(config={"plugin_handler_timeout": 0.5})

    def test_handler_timeout(self):
        """Handler který spí 10s musí být přerušen do 1s."""
        manager = self._make_manager()

        def slow_handler(text: str):
            time.sleep(10)
            return "never", "returned"

        start = time.time()
        result = manager.call_route(slow_handler, "test", plugin_name="slow_plugin")
        elapsed = time.time() - start

        assert result == (None, None)
        assert elapsed < 2.0, f"Timeout trval příliš dlouho: {elapsed:.1f}s"

    def test_handler_exception(self):
        """Handler který vyhodí výjimku musí vrátit (None, None)."""
        manager = self._make_manager()

        def broken_handler(text: str):
            raise RuntimeError("Simulovaná chyba handleru")

        result = manager.call_route(broken_handler, "test", plugin_name="broken_plugin")
        assert result == (None, None)
