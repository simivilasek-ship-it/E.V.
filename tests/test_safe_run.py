"""Testy pro safe_run helper v commands/utils.py."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from commands.utils import safe_run


class TestSafeRun:

    def test_uspesny_prikaz(self):
        r = safe_run(["python3", "-c", "print('ok')"])
        assert r["rc"] == 0
        assert "ok" in r["stdout"]
        assert r["timeout"] is False

    def test_neexistujici_prikaz(self):
        r = safe_run(["_prikaz_ktery_neexistuje_12345"])
        assert r["rc"] == -1
        assert "nenalezen" in r["stderr"]
        assert r["timeout"] is False

    def test_timeout(self):
        r = safe_run(["sleep", "10"], timeout=0.1)
        assert r["timeout"] is True
        assert r["rc"] == -1

    def test_navratovy_kod_chyba(self):
        r = safe_run(["python3", "-c", "import sys; sys.exit(42)"])
        assert r["rc"] == 42
        assert r["timeout"] is False

    def test_stderr_zachycen(self):
        r = safe_run(["python3", "-c", "import sys; sys.stderr.write('err\\n')"])
        assert "err" in r["stderr"]

    def test_cmd_musi_byt_list(self):
        with pytest.raises(ValueError):
            safe_run("echo hello")  # string místo listu

    def test_prazdny_cmd_vyhodi_chybu(self):
        with pytest.raises(ValueError):
            safe_run([])

    def test_bg_mod_nevrati_vystup(self):
        r = safe_run(["python3", "-c", "pass"], bg=True)
        assert r["rc"] == 0
        assert r["stdout"] == ""

    def test_bg_neexistujici_prikaz(self):
        r = safe_run(["_neexistuje_bg_"], bg=True)
        assert r["rc"] == -1
        assert "nenalezen" in r["stderr"]

    def test_stdout_a_stderr_oddelene(self):
        r = safe_run(["python3", "-c",
                      "import sys; print('out'); sys.stderr.write('err')"])
        assert "out" in r["stdout"]
        assert "err" in r["stderr"]

    def test_cwd_parametr(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            r = safe_run(["pwd"], cwd=d)
            assert r["rc"] == 0
            assert os.path.realpath(d) in os.path.realpath(r["stdout"].strip())

    def test_cmd_string_misto_listu(self):
        with pytest.raises(ValueError, match="list"):
            safe_run("ls -la")

    def test_velky_vystup(self):
        # safe_run musí zvládnout velký stdout bez OOM
        r = safe_run(["python3", "-c", "print('x' * 100_000)"])
        assert r["rc"] == 0
        assert len(r["stdout"]) > 90_000
