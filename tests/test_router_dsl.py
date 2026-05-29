"""
Testy pro RouterDSL — mini DSL pro LocalRouter.
"""
import sys
import os
import re
import pytest

# Přidej kořen projektu do sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from router_dsl import RouterDSL


# ──────────────────────────────────────────────────────────────────────
# 1. Kompilace — pattern bez slotů
# ──────────────────────────────────────────────────────────────────────
def test_compile_simple():
    dsl = RouterDSL()
    pattern = dsl.compile("ahoj svete")
    assert pattern.match("ahoj svete") is not None
    assert pattern.match("neco jineho") is None


# ──────────────────────────────────────────────────────────────────────
# 2. Kompilace — slot {num} matchuje čísla
# ──────────────────────────────────────────────────────────────────────
def test_compile_num_slot():
    dsl = RouterDSL()
    pattern = dsl.compile("hlasitost {num}")
    m = pattern.match("hlasitost 75")
    assert m is not None
    assert m.group("num") == "75"

    # Musí matchovat i desetinná čísla
    m2 = pattern.match("hlasitost 3.5")
    assert m2 is not None
    assert m2.group("num") == "3.5"

    # Nesmí matchovat text bez čísla
    assert pattern.match("hlasitost max") is None


# ──────────────────────────────────────────────────────────────────────
# 3. Kompilace — slot {text} matchuje cokoliv
# ──────────────────────────────────────────────────────────────────────
def test_compile_text_slot():
    dsl = RouterDSL()
    pattern = dsl.compile("zahraj {query}")
    m = pattern.match("zahraj bohemian rhapsody")
    assert m is not None
    assert m.group("query") == "bohemian rhapsody"


# ──────────────────────────────────────────────────────────────────────
# 4. Pravidlo — matchuje vstup a vrátí správný action
# ──────────────────────────────────────────────────────────────────────
def test_rule_match():
    dsl = RouterDSL()
    dsl.rule("zahraj {query}", action="youtube_play", param="query")

    action, params = dsl.match("zahraj despacito")
    assert action == "youtube_play"
    assert params["query"] == "despacito"


# ──────────────────────────────────────────────────────────────────────
# 5. coerce=int konvertuje string na int
# ──────────────────────────────────────────────────────────────────────
def test_rule_coerce_int():
    dsl = RouterDSL()
    dsl.rule("hlasitost {num}", action="volume", param="level", coerce=int)

    action, params = dsl.match("hlasitost 60")
    assert action == "volume"
    assert params["level"] == 60
    assert isinstance(params["level"], int)


# ──────────────────────────────────────────────────────────────────────
# 6. Lambda coerce — minuty → sekundy
# ──────────────────────────────────────────────────────────────────────
def test_rule_coerce_lambda():
    dsl = RouterDSL()
    dsl.rule("timer {num} minut", action="set_timer", param="seconds",
             coerce=lambda x: int(float(x)) * 60)

    action, params = dsl.match("timer 5 minut")
    assert action == "set_timer"
    assert params["seconds"] == 300  # 5 * 60


# ──────────────────────────────────────────────────────────────────────
# 7. Neregistrovaný vstup → (None, None)
# ──────────────────────────────────────────────────────────────────────
def test_no_match():
    dsl = RouterDSL()
    dsl.rule("hlasitost {num}", action="volume", param="level", coerce=int)

    action, params = dsl.match("napiš dopis")
    assert action is None
    assert params is None


# ──────────────────────────────────────────────────────────────────────
# 8. to_routes — vrátí list dict s 'pattern' a 'handler'
# ──────────────────────────────────────────────────────────────────────
def test_to_routes():
    dsl = RouterDSL()
    dsl.rule("hlasitost {num}", action="volume", param="level", coerce=int)
    dsl.rule("otevri {app}", action="open_app", param="app")

    routes = dsl.to_routes()
    assert isinstance(routes, list)
    assert len(routes) == 2

    # Každý prvek musí mít 'pattern', 'action', 'handler'
    for route in routes:
        assert "pattern" in route
        assert "action" in route
        assert "handler" in route
        assert isinstance(route["pattern"], re.Pattern)
        assert callable(route["handler"])

    # Otestuj handler prvního pravidla
    m = routes[0]["pattern"].match("hlasitost 80")
    assert m is not None
    result_params = routes[0]["handler"](m)
    assert result_params["level"] == 80
    assert isinstance(result_params["level"], int)
