# Backward-compatibility shim — real module lives in src/config_schema.py
from src.config_schema import *  # noqa: F401, F403
from src.config_schema import JarvisSettings, VoiceSettings, SecuritySettings, AgentSettings, validate_config  # noqa: F401
