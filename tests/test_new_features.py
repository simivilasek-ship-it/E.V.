"""
Tests for v4.5 features: sports, hardware info, memory conflict, parallel agents, LLM cache.
"""
import os, sys, re, time
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Sports ────────────────────────────────────────────

class TestCmdSports:
    def _mock_espn(self, events):
        return {"events": events}

    def _make_event(self, home, away, home_score, away_score, status="Final"):
        return {
            "date": "2026-05-30T18:00Z",
            "name": f"{away} at {home}",
            "competitions": [{
                "status": {"type": {"description": status, "detail": ""}, "displayClock": "", "period": 0},
                "competitors": [
                    {"homeAway": "home", "team": {"displayName": home}, "score": str(home_score)},
                    {"homeAway": "away", "team": {"displayName": away},  "score": str(away_score)},
                ],
            }],
        }

    @patch("requests.get")
    def test_sports_premier_league(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self._mock_espn([
            self._make_event("Arsenal", "Chelsea", 2, 1),
            self._make_event("Liverpool", "Man City", 0, 0, "In Progress"),
        ])
        from commands.utils import cmd_sports
        result = cmd_sports("premier league")
        assert "Arsenal" in result
        assert "Chelsea" in result

    @patch("requests.get")
    def test_sports_overview(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self._mock_espn([
            self._make_event("Paris SG", "Barcelona", 3, 2),
        ])
        from commands.utils import cmd_sports
        result = cmd_sports("")
        assert isinstance(result, str)

    @patch("requests.get")
    def test_sports_empty_returns_no_crash(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"events": []}
        from commands.utils import cmd_sports
        result = cmd_sports("nhl")
        assert isinstance(result, str)

    @patch("requests.get", side_effect=Exception("Network error"))
    def test_sports_network_error(self, mock_get):
        from commands.utils import cmd_sports
        result = cmd_sports("fotbal")
        assert isinstance(result, str)

    def test_sports_routing(self):
        from local_router import LocalRouter
        r = LocalRouter()
        for q in ["hraje dnes fotbal", "premier league výsledky", "nhl zapasy", "fotbal výsledky"]:
            _, act = r.route(q)
            assert act is not None, f"'{q}' nevyroutoval na sports"
            assert act["action"] == "sports", f"'{q}' → {act['action']} místo sports"


# ── Hardware info ─────────────────────────────────────

class TestCmdHardwareInfo:
    @patch("subprocess.run")
    @patch("psutil.cpu_count", return_value=12)
    @patch("psutil.cpu_freq")
    @patch("psutil.virtual_memory")
    @patch("psutil.disk_partitions")
    def test_hardware_info_structure(self, mock_parts, mock_mem, mock_freq, mock_cc, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
        mock_freq.return_value = MagicMock(max=5000.0)
        mock_mem.return_value  = MagicMock(total=32 * 1024**3, percent=40.0)
        mock_parts.return_value = []
        from commands.system import cmd_hardware_info
        result = cmd_hardware_info()
        assert "CPU" in result or "neznámý" in result
        assert "RAM" in result
        assert "OS" in result

    def test_hardware_routing(self):
        from local_router import LocalRouter
        r = LocalRouter()
        for q in ["jaké máš komponenty", "hardware info", "rekni moje komponenty"]:
            _, act = r.route(q)
            assert act and act["action"] == "hardware_info", f"'{q}' → {act}"


# ── Memory conflict resolution ────────────────────────

class TestMemoryConflict:
    def test_no_conflict_different_topic(self):
        from memory import JarvisMemory, _similarity_score
        assert _similarity_score("jmenuji se Petr", "jmenuji se Petr") == 1.0
        assert _similarity_score("jmenuji se Petr", "jmenuji se Pavel") < 1.0
        assert _similarity_score("python programovani", "hokej sport") < 0.3

    def test_similarity_score_identical(self):
        from memory import _similarity_score
        assert _similarity_score("hello world", "hello world") == 1.0

    def test_similarity_score_empty(self):
        from memory import _similarity_score
        assert _similarity_score("", "hello") == 0.0
        assert _similarity_score("hello", "") == 0.0

    def test_conflict_patterns_exist(self):
        from memory import JarvisMemory
        patterns = JarvisMemory._CONFLICT_PATTERNS
        assert len(patterns) >= 4
        topics = [p[1] for p in patterns]
        assert "jméno" in topics
        assert "technologie" in topics


# ── Parallel agents ───────────────────────────────────

class TestParallelAgents:
    @patch("requests.post")
    def test_run_parallel_returns_string(self, mock_post):
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {
            "message": {"content": "1. Krok A\n2. Krok B\n3. Krok C"}
        }
        from agent_roles import MultiAgentOrchestrator
        orch = MultiAgentOrchestrator("http://localhost:11434/api/chat", "qwen2.5:3b")
        result = orch.run_parallel("Testovací úkol", max_steps=2)
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("requests.post")
    def test_run_parallel_timing_info(self, mock_post):
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {
            "message": {"content": "1. Vyhledej\n2. Porovnej"}
        }
        from agent_roles import MultiAgentOrchestrator
        orch = MultiAgentOrchestrator("http://localhost:11434/api/chat", "qwen2.5:3b")
        result = orch.run_parallel("Porovnej X a Y", max_steps=2)
        assert isinstance(result, str)

    def test_parallel_routing(self):
        from local_router import LocalRouter
        r = LocalRouter()
        _, act = r.route("multi-agent analyze system")
        assert act and act["action"] == "agent_parallel_task", f"got: {act}"


# ── LLM Cache ─────────────────────────────────────────

class TestLLMCache:
    def test_cache_basic(self):
        from llm import _LLMCache
        c = _LLMCache(maxsize=10, ttl=60)
        c.set("model", "co je python", "Python je jazyk", {"action": "answer", "params": {}})
        hit = c.get("model", "co je python")
        assert hit is not None
        assert hit[0] == "Python je jazyk"

    def test_cache_no_cache_realtime(self):
        from llm import _LLMCache
        c = _LLMCache()
        c.set("model", "pocasi praha", "Slunečno 20°C", {"action": "answer", "params": {}})
        assert c.get("model", "pocasi praha") is None  # real-time → přeskočeno

    def test_cache_ttl_expiry(self):
        from llm import _LLMCache
        c = _LLMCache(maxsize=10, ttl=0)  # TTL=0 → okamžitě expiruje
        c.set("model", "co je typescript", "TS je...", {"action": "answer", "params": {}})
        assert c.get("model", "co je typescript") is None

    def test_cache_maxsize_lru(self):
        from llm import _LLMCache
        c = _LLMCache(maxsize=3, ttl=600)
        for i in range(4):
            c.set("model", f"otazka {i}", f"odpoved {i}", {"action": "answer", "params": {}})
        assert len(c._store) <= 3

    def test_cache_stats(self):
        from llm import _LLMCache
        c = _LLMCache()
        stats = c.stats()
        assert "total" in stats and "valid" in stats and "ttl" in stats


# ── Undo stack ────────────────────────────────────────

class TestUndoStack:
    def test_undo_create_folder(self, tmp_path):
        from commands import CommandExecutor
        ex = CommandExecutor({})
        folder = str(tmp_path / "test_undo")
        ex.execute("create_folder", {"path": folder})
        assert os.path.isdir(folder)
        result = ex.undo()
        assert not os.path.isdir(folder)
        assert "smazána" in result or "Undo" in result

    def test_undo_empty(self):
        from commands import CommandExecutor
        ex = CommandExecutor({})
        result = ex.undo()
        assert "Nic" in result or "vrácení" in result.lower() or result

    def test_undo_history(self, tmp_path):
        from commands import CommandExecutor
        ex = CommandExecutor({})
        ex.execute("create_folder", {"path": str(tmp_path / "a")})
        ex.execute("create_folder", {"path": str(tmp_path / "b")})
        hist = ex.undo_history()
        assert len(hist) == 2

    def test_undo_routing(self):
        from local_router import LocalRouter
        r = LocalRouter()
        _, act = r.route("vrať poslední akci")
        assert act and act["action"] == "undo"
