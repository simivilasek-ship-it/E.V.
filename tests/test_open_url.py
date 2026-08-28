"""Otevírání webů: hellspy.cz bez https://, mluvená tečka, delší odpověď."""
from unittest.mock import patch

from commands.files import extract_web_url, normalize_web_url
from local_router import LocalRouter


def test_normalize_adds_https():
    assert normalize_web_url("hellspy.cz") == "https://hellspy.cz"
    assert normalize_web_url("https://hellspy.cz") == "https://hellspy.cz"
    assert normalize_web_url("www.hellspy.cz") == "https://www.hellspy.cz"


def test_extract_bare_domain():
    assert extract_web_url("hellspy.cz") == "https://hellspy.cz"
    assert extract_web_url("Otevři stránku hellspy.cz") == "https://hellspy.cz"
    assert extract_web_url("jdi na https://hellspy.cz/foo") == "https://hellspy.cz/foo"


def test_extract_spoken_dot():
    assert extract_web_url("hellspy tečka cz") == "https://hellspy.cz"
    assert extract_web_url("otevři hellspy tecka cz") == "https://hellspy.cz"


def test_route_open_page_without_scheme():
    msg, action = LocalRouter().route("Otevři stránku hellspy.cz")
    assert action is not None
    assert action["action"] == "open_url"
    assert action["params"]["url"] == "https://hellspy.cz"
    assert "hellspy.cz" in msg
    assert "prohlížeči" in msg.lower() or "prohlizeci" in msg.lower()


def test_route_bare_domain():
    _, action = LocalRouter().route("hellspy.cz")
    assert action["action"] == "open_url"
    assert action["params"]["url"] == "https://hellspy.cz"


def test_route_does_not_open_question_about_domain():
    _, action = LocalRouter().route("co je hellspy.cz")
    assert action is None or action.get("action") != "open_url"


@patch("commands.files.open_in_browser", return_value=True)
def test_executor_opens_normalized_url(mock_open):
    from commands import CommandExecutor
    result = CommandExecutor({}).execute("open_url", {"url": "hellspy.cz"})
    mock_open.assert_called_once_with("https://hellspy.cz")
    assert result == "ok"
