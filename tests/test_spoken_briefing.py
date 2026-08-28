"""Mluvený úvodní briefing — počasí a kalendář."""
from datetime import datetime

from src.morning_briefing import spoken_hello, spoken_home_briefing


def test_spoken_hello_is_a_greeting():
    text = spoken_hello("Simi")
    assert "Čau Simi" in text
    assert "Jsem tady" in text or "Pořád tady" in text
    assert "systémy" not in text.lower()
    assert len(text) < 80


def test_spoken_briefing_sounds_human():
    text = spoken_home_briefing(
        "Simi",
        now=datetime(2026, 8, 20, 19, 5),
        weather={"city": "Praha", "desc": "polojasno", "temp": 18},
        events=[{"summary": "Call s týmem", "time": "20:00"}],
        calendar_configured=True,
    )
    assert "Čau Simi" in text
    assert "nic nehoří" in text
    assert "18" in text
    assert "Call s týmem" in text
    assert "20:00" in text
    assert "jako první" in text
    assert "Systémy běží" not in text
    assert "*" not in text
    assert "#" not in text


def test_spoken_briefing_hot_weather_has_flavor():
    text = spoken_home_briefing(
        "Simi",
        now=datetime(2026, 8, 20, 15, 0),
        weather={"city": "Praha", "desc": "jasno", "temp": 27},
        events=[],
        calendar_configured=True,
        include_hello=False,
    )
    assert "27" in text
    assert "peklíčko" in text
    assert "srpnové" in text


def test_spoken_briefing_without_calendar():
    text = spoken_home_briefing(
        "Simi",
        now=datetime(2026, 8, 20, 8, 0),
        weather={"city": "Praha", "desc": "jasno", "temp": 12},
        events=[],
        calendar_configured=False,
    )
    assert "Dobré ráno" in text
    assert "Kalendář" in text


def test_spoken_briefing_empty_calendar():
    text = spoken_home_briefing(
        "Ana",
        now=datetime(2026, 8, 20, 21, 0),
        weather=None,
        events=[],
        calendar_configured=True,
    )
    assert "Ana" in text
    assert "tichý" in text
    assert "Počasí" in text
