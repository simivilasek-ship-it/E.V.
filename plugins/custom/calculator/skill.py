"""JARVIS Skill — Kalkulačka"""
import re
import math
import logging

logger = logging.getLogger(__name__)

_CALC_RE = re.compile(
    r"\b(vypocitej|spocitej|kolik\s+je|calculate|calc)\b(.+)",
    re.IGNORECASE,
)
_PERCENT_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*%\s+z\s+(\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)
_EXPR_RE = re.compile(
    r"[\d\s\+\-\*\/\^\(\)\.\,sqrtSQRTpowPOWabsABS]+",
)

_SAFE_NAMES = {
    "sqrt": math.sqrt, "pow": math.pow, "abs": abs,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "log": math.log, "log10": math.log10, "pi": math.pi, "e": math.e,
}


def _safe_eval(expr: str) -> str:
    expr = expr.strip().replace(",", ".").replace("^", "**")
    try:
        result = eval(expr, {"__builtins__": {}}, _SAFE_NAMES)
        if isinstance(result, float) and result == int(result):
            return str(int(result))
        return f"{result:.6g}"
    except Exception:
        return None


def _handle_calc(text: str):
    # Procento: "15% z 200"
    pm = _PERCENT_RE.search(text)
    if pm:
        pct = float(pm.group(1).replace(",", "."))
        val = float(pm.group(2).replace(",", "."))
        result = pct / 100 * val
        return f"{pct}% z {val} = {result:.4g}", {"action": "calculate",
                                                    "params": {"expression": f"{pct}/100*{val}"}}

    # Obecný výraz
    m = _CALC_RE.search(text)
    if not m:
        return None, None

    expr = m.group(2).strip()
    result = _safe_eval(expr)
    if result is None:
        return None, None

    return f"{expr} = {result}", {"action": "calculate", "params": {"expression": expr}}


def get_routes():
    return [
        {"pattern": _PERCENT_RE, "handler": _handle_calc},
        {"pattern": _CALC_RE, "handler": _handle_calc},
    ]


def get_actions():
    return {}
