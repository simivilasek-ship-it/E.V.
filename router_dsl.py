"""
JARVIS — Mini DSL pro LocalRouter
Kompiluje pattern stringy do regex + handler mapování.

Syntaxe:
  "{text}" = zachytí libovolný text (group name = text)
  "{num}"  = zachytí číslo (automaticky konvertuje na int/float)
  "{app}"  = zachytí jméno aplikace
"""

import re
from typing import Callable, Optional


# Typy slotů → regex fragment
_SLOT_PATTERNS = {
    "num":  r"(?P<{name}>\d+(?:\.\d+)?)",   # číslo (int nebo float)
    "app":  r"(?P<{name}>[a-zA-Z0-9\s]+?)", # název aplikace
}
_SLOT_DEFAULT = r"(?P<{name}>.+)"           # cokoliv (text, query, …)

# Regex pro detekci slotů v DSL patternu
_SLOT_RE = re.compile(r"\{(\w+)\}")


class RouterDSL:
    """
    Kompiluje DSL pravidla do LocalRouter compatible routů.

    Syntaxe:
      "{text}" = zachytí libovolný text (group name = text)
      "{num}"  = zachytí číslo (automaticky konvertuje na int/float)
      "{app}"  = zachytí jméno aplikace

    Příklad:
      dsl = RouterDSL()
      dsl.rule('otevři {app}', action='open_app', param='app')
      dsl.rule('hlasitost na {num}', action='volume', param='level', coerce=int)
    """

    def __init__(self):
        # Každý záznam: (compiled_regex, action, param_name, coerce, extra_params)
        self._rules: list[tuple] = []

    # ------------------------------------------------------------------
    def compile(self, pattern: str) -> re.Pattern:
        """Převede DSL pattern na regex s named groups.

        {num}  → (?P<num>\\d+(?:\\.\\d+)?)
        {app}  → (?P<app>[a-zA-Z0-9\\s]+?)
        {text} → (?P<text>.+)
        {xyz}  → (?P<xyz>.+)
        """
        regex_str = re.escape(pattern)

        # re.escape obalí {…} jako \\{…\\} – rozbalíme je zpět
        # aby bylo snadné hledat sloty.
        regex_str = regex_str.replace(r"\{", "{").replace(r"\}", "}")

        def replace_slot(m: re.Match) -> str:
            slot_name = m.group(1)
            slot_type = slot_name  # "num", "app", nebo cokoli jiného
            template = _SLOT_PATTERNS.get(slot_type, _SLOT_DEFAULT)
            return template.format(name=slot_name)

        regex_str = _SLOT_RE.sub(replace_slot, regex_str)
        return re.compile(r"^\s*" + regex_str + r"\s*$", re.IGNORECASE)

    # ------------------------------------------------------------------
    def rule(
        self,
        pattern: str,
        action: str,
        param: Optional[str] = None,
        coerce: Optional[Callable] = None,
        extra_params: Optional[dict] = None,
    ) -> None:
        """Registruje pravidlo.

        Args:
            pattern:      DSL pattern (např. 'hlasitost {num}')
            action:       název akce (např. 'volume')
            param:        název výstupního parametru (např. 'level')
                          Pokud None, použije se jméno slotu přímo.
            coerce:       volitelná konverze hodnoty (int, float, lambda …)
            extra_params: statické parametry přidané k výsledku
        """
        compiled = self.compile(pattern)
        self._rules.append((compiled, action, param, coerce, extra_params or {}))

    # ------------------------------------------------------------------
    def match(self, text: str) -> tuple:
        """Zkusí matchnout text proti všem pravidlům.

        Returns:
            (action, params) nebo (None, None)
        """
        for compiled, action, param, coerce, extra_params in self._rules:
            m = compiled.match(text)
            if m is None:
                continue

            groups = m.groupdict()
            params = dict(extra_params)

            if groups:
                # Pokud je jen jeden slot a param je zadán, remapujeme slot na param
                slot_names = list(groups.keys())
                if param and len(slot_names) == 1:
                    raw_value = groups[slot_names[0]]
                    value = coerce(raw_value) if coerce else raw_value
                    params[param] = value
                else:
                    # Více slotů — každý slot vložíme pod vlastním jménem
                    for slot_name, raw_value in groups.items():
                        if raw_value is None:
                            continue
                        value = coerce(raw_value) if coerce else raw_value
                        key = param if (param and slot_name == slot_names[0]) else slot_name
                        params[key] = value

            return action, params

        return None, None

    # ------------------------------------------------------------------
    def to_routes(self) -> list[dict]:
        """Vrátí seznam kompatibilní s LocalRouter._routes formátem.

        Každý prvek obsahuje:
          'pattern' : zkompilovaný regex
          'action'  : název akce
          'handler' : callable který přijme match objekt a vrátí params dict
        """
        routes = []
        for compiled, action, param, coerce, extra_params in self._rules:

            # Capture variables for closure
            def make_handler(_param, _coerce, _extra):
                def handler(m: re.Match) -> dict:
                    groups = m.groupdict()
                    p = dict(_extra)
                    slot_names = list(groups.keys())
                    if _param and slot_names:
                        raw = groups[slot_names[0]]
                        if raw is not None:
                            p[_param] = _coerce(raw) if _coerce else raw
                    else:
                        for sn, rv in groups.items():
                            if rv is not None:
                                p[sn] = _coerce(rv) if _coerce else rv
                    return p
                return handler

            routes.append({
                "pattern": compiled,
                "action":  action,
                "handler": make_handler(param, coerce, extra_params),
            })
        return routes
