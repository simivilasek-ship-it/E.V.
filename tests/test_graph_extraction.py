import pytest

from memory import _extract_entities_simple

pytestmark = [pytest.mark.unit]


def test_extract_bratr_relation():
    triplets = _extract_entities_simple("Můj brácha Jirka začal programovat v Rustu")
    assert ("Ty", "MÁ_BRATRA", "Jirka") in triplets


def test_extract_learning_relation():
    triplets = _extract_entities_simple("Jirka se učí Rust")
    assert any(t[0] == "Jirka" and t[1] in ("UČÍ_SE", "PROGRAMUJE_V") and t[2] == "Rust" for t in triplets)
