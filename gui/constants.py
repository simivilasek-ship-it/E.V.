"""
Sdílené barvy a konstanty pro JARVIS GUI.
"""

BG      = "#070b12"
BG2     = "#0b1220"
BG3     = "#0f1a2e"
FG      = "#e2f0ff"
FG2     = "#7ea8d4"
BORDER  = "#1a3050"
CYAN    = "#00d4ff"
CYAN2   = "#0099bb"
GREEN   = "#00e676"
RED     = "#ff5252"
PURPLE  = "#7c4dff"
LBLUE   = "#40c4ff"

ORB_COLORS = {
    "idle":      "#1565c0",
    "listening": "#00d4ff",
    "thinking":  "#7c4dff",
    "speaking":  "#00e676",
}
ORB_DARK = {
    "idle":      "#0d3a7a",
    "listening": "#005577",
    "thinking":  "#3d1a80",
    "speaking":  "#006633",
}
STATE_LABELS = {
    "idle":      "● IDLE",
    "listening": "● LISTENING",
    "thinking":  "● THINKING",
    "speaking":  "● SPEAKING",
}


def blend(color: str, bg: str, alpha: float) -> str:
    def p(h):
        h = h.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    cr, cg, cb = p(color)
    br, bg_, bb = p(bg)
    a = max(0.0, min(1.0, alpha))
    return f"#{int(br+(cr-br)*a):02x}{int(bg_+(cg-bg_)*a):02x}{int(bb+(cb-bb)*a):02x}"


def lerp(a: str, b: str, t: float) -> str:
    return blend(b, a, t)
