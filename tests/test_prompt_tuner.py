"""Tests for PromptTuner and SelfDebuggingAgent."""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prompt_tuner import PromptTuner, PromptVariant


def make_tuner():
    """Create a fresh PromptTuner without loading from disk."""
    t = object.__new__(PromptTuner)
    t._scores = {}
    for vid, prompt in PromptTuner.VARIANTS.items():
        t._scores[vid] = PromptVariant(variant_id=vid, system_prompt=prompt)
    return t


def test_get_best_variant_explores_unused():
    """A variant with 0 uses should be returned immediately (explore first)."""
    t = make_tuner()
    # Mark all but one as used
    variants = list(t._scores.values())
    for v in variants[1:]:
        v.uses = 5
        v.positive_feedback = 3
    # First variant has uses=0 — should be selected for exploration
    result = t.get_best_variant()
    assert result == variants[0].system_prompt


def test_record_use_increments():
    """record_use should increment uses by 1."""
    t = make_tuner()
    t._save = lambda: None  # disable disk write
    vid = "stručný"
    before = t._scores[vid].uses
    t.record_use(vid, response_length=100)
    assert t._scores[vid].uses == before + 1


def test_record_feedback_positive():
    """record_feedback positive=True should increment positive_feedback."""
    t = make_tuner()
    t._save = lambda: None
    vid = "technický"
    before = t._scores[vid].positive_feedback
    t.record_feedback(vid, positive=True)
    assert t._scores[vid].positive_feedback == before + 1


def test_score_calculation():
    """3 uses, 2 positive → score = (2 + 0.5) / (3 + 1) = 0.625."""
    v = PromptVariant(variant_id="test", system_prompt="test", uses=3, positive_feedback=2)
    expected = (2 + 0.5) / (3 + 1)
    assert abs(v.score - expected) < 1e-9


def test_self_debugging_has_error():
    """has_error detects error patterns correctly."""
    from agent_roles import SelfDebuggingAgent
    agent = SelfDebuggingAgent("http://localhost:11434/api/chat", "test-model")
    assert agent.has_error("Traceback (most recent call last):\n  File...") is True
    assert agent.has_error("Výsledek: 42") is False
