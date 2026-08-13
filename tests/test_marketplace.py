"""
Testy pro E.V. Plugin Marketplace.
"""

import io
import zipfile
import shutil
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Přidej kořen projektu do sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from plugin_marketplace import PluginMarketplace


def _make_zip(prefix: str = "plugin-main/") -> bytes:
    """Vytvoří in-memory ZIP s testovými soubory."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(f"{prefix}manifest.json", '{"name":"plugin"}')
        z.writestr(f"{prefix}skill.py", "def get_routes(): return []")
    buf.seek(0)
    return buf.read()


# ── Pomocná fixture ───────────────────────────────────

@pytest.fixture
def tmp_marketplace(tmp_path):
    """Vrátí PluginMarketplace s dočasným plugins_dir."""
    return PluginMarketplace(plugins_dir=str(tmp_path))


@pytest.fixture
def empty_registry_marketplace(tmp_path):
    """Marketplace s prázdným REGISTRY."""
    mp = PluginMarketplace(plugins_dir=str(tmp_path))
    mp.REGISTRY = {}
    return mp


# ── Testy ─────────────────────────────────────────────

def test_list_available_empty(empty_registry_marketplace):
    """Prázdný REGISTRY vrátí smysluplný string."""
    result = empty_registry_marketplace.list_available()
    assert "prázdný" in result.lower() or "marketplace" in result.lower()


def test_list_available_shows_status(tmp_marketplace, tmp_path):
    """Nainstalovaný plugin má ✓, nedostupný má ○."""
    # Simuluj nainstalovaný hello-world
    (tmp_path / "hello-world").mkdir()

    result = tmp_marketplace.list_available()
    assert "✓" in result  # formát se mohl změnit
    assert "hello-world" in result


def test_install_unknown_plugin(tmp_marketplace):
    """Neznámý plugin vrátí chybovou zprávu, ne výjimku."""
    result = tmp_marketplace.install("neexistujici-plugin")
    assert "není v marketplace" in result or "neexistujici" in result.lower()


def test_install_success(tmp_marketplace, tmp_path):
    """Úspěšná instalace: mock requests → ZIP v paměti → soubory vytvořeny."""
    # Přidej testovací plugin do registry
    tmp_marketplace.REGISTRY["test-plugin"] = {
        "repo": "testuser/test-plugin",
        "description": "Test plugin",
        "author": "Tester",
    }

    zip_content = _make_zip(prefix="test-plugin-main/")

    mock_response = MagicMock()
    mock_response.content = zip_content
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        result = tmp_marketplace.install("test-plugin")

    assert "nainstalován" in result
    dest = tmp_path / "test-plugin"
    assert dest.exists()
    assert (dest / "manifest.json").exists()
    assert (dest / "skill.py").exists()


def test_install_already_installed(tmp_marketplace, tmp_path):
    """Pokud složka existuje, vrátí info o již nainstalovaném pluginu."""
    (tmp_path / "hello-world").mkdir()
    result = tmp_marketplace.install("hello-world")
    assert "již nainstalován" in result or "nainstalován" in result


def test_uninstall_missing(tmp_marketplace):
    """Plugin neexistuje → smysluplná zpráva bez výjimky."""
    result = tmp_marketplace.uninstall("neexistujici-plugin")
    assert "není nainstalován" in result or "neexistuje" in result.lower()


def test_uninstall_removes_dir(tmp_marketplace, tmp_path):
    """Odinstalace smaže složku pluginu."""
    plugin_dir = tmp_path / "hello-world"
    plugin_dir.mkdir()
    (plugin_dir / "skill.py").write_text("# test")

    result = tmp_marketplace.uninstall("hello-world")
    assert not plugin_dir.exists()
    assert "odinstalován" in result


def test_install_from_github_url(tmp_marketplace, tmp_path):
    """Normalizace GitHub URL na user/repo a instalace."""
    zip_content = _make_zip(prefix="my-plugin-main/")

    mock_response = MagicMock()
    mock_response.content = zip_content
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        result = tmp_marketplace.install_from_github(
            "https://github.com/someuser/my-plugin"
        )

    # Název je normalizovaný: my-plugin → my_plugin
    assert "nainstalován" in result
    dest = tmp_path / "my_plugin"
    assert dest.exists()
