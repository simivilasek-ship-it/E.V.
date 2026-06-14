# Backward-compatibility shim — real module lives in src/morning_briefing.py
from src.morning_briefing import *  # noqa: F401, F403
from src.morning_briefing import MorningBriefing, send_briefing, schedule_briefing  # noqa: F401
