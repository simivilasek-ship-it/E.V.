"""Unit tests for morning briefing."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from src.morning_briefing import MorningBriefing, send_briefing

pytestmark = [pytest.mark.unit]


def test_generate_includes_user_name():
    text = MorningBriefing().generate(user_name="Tester")
    assert "Tester" in text
    assert "Simone" not in text or "Tester" in text
    assert "E.V." in text
    assert "Datum" in text


def test_generate_git_clean_message():
    with patch("src.morning_briefing._find_dirty_repos", return_value=[]):
        with patch("src.morning_briefing._get_yesterday_summary", return_value="klid"):
            text = MorningBriefing().generate("Ana")
    assert "čisté" in text or "Git" in text
    assert "klid" in text


def test_generate_lists_dirty_repos():
    with patch("src.morning_briefing._find_dirty_repos", return_value=["E.V.", "portfolio"]):
        text = MorningBriefing().generate("Ana")
    assert "`E.V.`" in text
    assert "`portfolio`" in text


def test_send_briefing_writes_log(tmp_path, monkeypatch):
    monkeypatch.setattr("src.morning_briefing._JARVIS_DIR", tmp_path)
    monkeypatch.setattr("src.morning_briefing._BRIEFING_LOG", tmp_path / "briefing.log")
    with patch("src.morning_briefing.subprocess.run", side_effect=FileNotFoundError):
        text = send_briefing()
    assert text
    assert (tmp_path / "briefing.log").is_file()
    assert "E.V." in (tmp_path / "briefing.log").read_text(encoding="utf-8")


def test_find_dirty_repos_handles_missing_dirs():
    from src.morning_briefing import _find_dirty_repos

    with patch("src.morning_briefing._GIT_SEARCH_DIRS", []):
        assert _find_dirty_repos() == []
