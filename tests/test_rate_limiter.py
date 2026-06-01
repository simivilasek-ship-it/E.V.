"""
Testy pro LLMRateLimiter v llm.py.
"""

import sys
import time
from unittest.mock import patch
import pytest

sys.path.insert(0, ".")

from llm import LLMRateLimiter


class TestLLMRateLimiter:

    def test_allowed_under_limit(self):
        """První dotaz musí být povolen — jsme hluboko pod limitem."""
        rl = LLMRateLimiter(max_per_minute=10)
        assert rl.is_allowed() is True

    def test_blocked_over_limit(self):
        """Po N dotazech musí is_allowed() vrátit False."""
        limit = 5
        rl = LLMRateLimiter(max_per_minute=limit)
        # Vyčerpej limit
        for _ in range(limit):
            rl.is_allowed()
        # Další dotaz musí být zamítnut
        assert rl.is_allowed() is False

    def test_stats_counts_calls(self):
        """stats() vrátí správný počet volání za poslední minutu."""
        rl = LLMRateLimiter(max_per_minute=20)
        for _ in range(7):
            rl.is_allowed()
        s = rl.stats()
        assert s["calls_last_minute"] == 7
        assert s["limit"] == 20

    def test_old_calls_expire(self):
        """Volání starší 60s se nepočítají do limitu (mock time.monotonic)."""
        rl = LLMRateLimiter(max_per_minute=5)
        # Simuluj 4 volání v t=0 (stará, za hranicí 60s)
        fake_old = 0.0
        with patch("time.monotonic", return_value=fake_old):
            for _ in range(4):
                rl.is_allowed()

        # Posuň čas o 61s — stará volání vyexpirují
        fake_now = 61.0
        with patch("time.monotonic", return_value=fake_now):
            # Interně deque pročistí staré záznamy a uloží nové
            result = rl.is_allowed()
            assert result is True, "Po expiraci starých volání musí být nové volání povoleno"
            s = rl.stats()
            # Po uklizení starých by mělo být jen 1 nové volání
            assert s["calls_last_minute"] == 1

    def test_wait_if_needed_no_block(self):
        """Pod limitem wait_if_needed() okamžitě vrátí bez čekání."""
        rl = LLMRateLimiter(max_per_minute=30)
        start = time.monotonic()
        rl.wait_if_needed()
        elapsed = time.monotonic() - start
        # Musí vrátit v méně než 100ms (okamžitě)
        assert elapsed < 0.1, f"wait_if_needed() čekalo příliš dlouho: {elapsed:.3f}s"
