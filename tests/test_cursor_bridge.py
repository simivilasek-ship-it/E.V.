from unittest.mock import MagicMock, patch

from cursor_bridge import ask_cursor, extract_cursor_prompt
from local_router import LocalRouter


def test_extract_says_cursor_task():
    assert extract_cursor_prompt(
        "Řekni Cursoru ať opraví greeting",
        "rekni cursoru at opravi greeting",
    ) == "opraví greeting"


def test_extract_connect_phrase():
    prompt = extract_cursor_prompt(
        "Spoj se s Cursorem a přidej test na pozdrav",
        "spoj se s cursorem a pridej test na pozdrav",
    )
    assert prompt is not None
    assert "přidej test" in prompt


def test_extract_czech_stt_kurzor():
    prompt = extract_cursor_prompt(
        "Řekni kurzoru ať napíše ahoj do README",
        "rekni kurzoru at napise ahoj do readme",
    )
    assert prompt is not None
    assert "ahoj" in prompt.lower()


def test_extract_ignores_weather():
    assert extract_cursor_prompt("Jaké je počasí v Praze", "jake je pocasi v praze") is None


def test_route_ask_cursor():
    msg, action = LocalRouter().route("Řekni Cursoru ať opraví greeting")
    assert action is not None
    assert action["action"] == "ask_cursor"
    assert "greeting" in action["params"]["prompt"]
    assert "Cursor" in msg


def test_route_time_is_not_cursor():
    _, action = LocalRouter().route("kolik je hodin")
    assert action is not None
    assert action["action"] != "ask_cursor"


def test_ask_cursor_without_key(monkeypatch):
    monkeypatch.delenv("CURSOR_API_KEY", raising=False)
    text = ask_cursor("Oprav greeting", config={"cursor_api_key": ""})
    assert "CURSOR_API_KEY" in text


def test_ask_cursor_uses_sdk(tmp_path):
    import sys

    run = MagicMock()
    result = MagicMock()
    result.status = "finished"
    result.result = "Hotovo. Greeting je lidštější."
    run.wait.return_value = result
    run.text.return_value = "Hotovo. Greeting je lidštější."

    agent = MagicMock()
    agent.agent_id = "local-test"
    agent.send.return_value = run
    agent.__enter__.return_value = agent
    agent.__exit__.return_value = False

    err_cls = type("CursorAgentError", (Exception,), {})
    fake = MagicMock()
    fake.Agent = MagicMock()
    fake.Agent.create.return_value = agent
    fake.Agent.resume.side_effect = err_cls("no previous")
    fake.AgentOptions = MagicMock()
    fake.LocalAgentOptions = MagicMock()
    fake.CursorAgentError = err_cls

    with patch("cursor_bridge._STATE_PATH", tmp_path / "cursor_agent.json"), \
         patch.dict(sys.modules, {"cursor_sdk": fake}):
        text = ask_cursor(
            "Oprav greeting",
            config={"cursor_api_key": "cursor_test", "cursor_workspace": str(tmp_path)},
        )

    assert "Hotovo" in text
    agent.send.assert_called_once()
