from plugins.custom.greeting.skill import _handle_greeting, get_routes


def test_standalone_ahoj_is_greeting():
    msg, action = _handle_greeting("ahoj")
    assert action["action"] == "answer"
    assert "ráno" in msg.lower() or "den" in msg.lower() or "večer" in msg.lower()


def test_ahoj_with_question_is_not_greeting_route():
    routes = get_routes()
    greeting = next(r for r in routes if r["handler"].__name__ == "_handle_greeting")
    assert greeting["pattern"].search("ahoj")
    assert greeting["pattern"].search("Ahoj Simi")
    assert not greeting["pattern"].search("ahoj jak se máš")
    assert not greeting["pattern"].search("ahoj, co děláš")
