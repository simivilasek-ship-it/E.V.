"""Unit tests for UserProfile."""
from __future__ import annotations

import pytest

from user_profile import UserProfile

pytestmark = [pytest.mark.unit]


@pytest.fixture
def profile(tmp_path):
    return UserProfile(path=tmp_path / "profile.json")


def test_set_get_remove(profile):
    profile.set("jméno", "Petr", confidence=0.9, source="manual")
    assert profile.get("jméno") == "Petr"
    assert profile.get("neexistuje", "x") == "x"
    assert profile.remove("jméno") is True
    assert profile.get("jméno") is None
    assert profile.remove("jméno") is False


def test_confidence_does_not_overwrite_higher(profile):
    profile.set("město", "Brno", confidence=0.9)
    profile.set("město", "Praha", confidence=0.4)
    assert profile.get("město") == "Brno"


def test_confidence_overwrite_equal_or_higher(profile):
    profile.set("město", "Brno", confidence=0.5)
    profile.set("město", "Praha", confidence=0.8)
    assert profile.get("město") == "Praha"


def test_extract_name_and_city(profile):
    found = profile.extract_from_text("Jmenuji se Karel a bydlím v Ostravě.")
    assert "jméno" in found
    assert profile.get("jméno") == "karel"


def test_extract_interests_appends(profile):
    profile.extract_from_text("Mám rád python")
    profile.extract_from_text("Mám rád linux")
    hobbies = profile.get("zájmy")
    assert isinstance(hobbies, list)
    assert any("python" in str(x) for x in hobbies)


def test_summary_and_persistence(tmp_path):
    path = tmp_path / "profile.json"
    p1 = UserProfile(path=path)
    p1.set("jméno", "Eva")
    p1.set("zájmy", ["hudba"])
    summary = p1.summary()
    assert "Eva" in summary
    assert "hudba" in summary

    p2 = UserProfile(path=path)
    assert p2.get("jméno") == "Eva"


def test_empty_summary(profile):
    assert profile.summary() == ""
