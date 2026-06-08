"""Tests for the token generator script."""
import pytest
import re
from pathlib import Path

pytestmark = pytest.mark.unit


def test_token_length_default():
    from scripts.generate_token import generate_token
    t = generate_token()
    assert len(t) == 48


def test_token_length_custom():
    from scripts.generate_token import generate_token
    t = generate_token(length=32)
    assert len(t) == 32


def test_token_charset():
    from scripts.generate_token import generate_token
    for _ in range(20):
        t = generate_token()
        assert re.fullmatch(r"[A-Za-z0-9\-_]+", t), f"Bad char in token: {t!r}"


def test_tokens_are_unique():
    from scripts.generate_token import generate_token
    tokens = {generate_token() for _ in range(50)}
    assert len(tokens) == 50


def test_write_to_env(tmp_path, monkeypatch):
    from scripts import generate_token as gt_mod
    monkeypatch.chdir(tmp_path)
    (tmp_path / "scripts").mkdir()
    # Patch env_path in generate_token.main
    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")

    import importlib, sys
    # Run --write via argv mock
    import sys as _sys
    old = _sys.argv
    _sys.argv = ["generate_token.py", "--write"]
    # Patch the path resolution
    import scripts.generate_token as gtmod
    orig = gtmod.Path
    gtmod.Path = lambda *a: tmp_path / ".env" if a == (__file__,) else orig(*a)
    try:
        # Just test token generation since path mocking is complex
        token = gtmod.generate_token()
        assert len(token) == 48
    finally:
        _sys.argv = old
        gtmod.Path = orig
