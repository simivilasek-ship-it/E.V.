from src.personality import EVPersonality


def test_greeting_sounds_like_jarvis():
    text = EVPersonality().get_greeting("Simi")
    assert "Čau Simi" in text
    assert "Jsem tady" in text or "Pořád tady" in text
    assert "systémy" not in text.lower()
    assert len(text) < 120


def test_no_llm_reply_mentions_what_user_said():
    text = EVPersonality().no_llm_reply("ahoj jak se máš", "Simi")
    assert "ahoj jak se máš" in text
    assert "Ollama" in text or "Groq" in text
    assert text != EVPersonality().no_llm_reply("kolik je hodin", "Simi")


def test_system_prompt_asks_for_spoken_replies():
    prompt = EVPersonality().build_system_prompt(user_name="Simi")
    assert "JARVIS" in prompt
    assert "lidsky" in prompt
    assert "ne jako robot" in prompt
    assert "krátké" in prompt.lower()
    assert "Nezačínej znovu pozdravem" in prompt
    assert "Stejnou uvítací větu" in prompt
