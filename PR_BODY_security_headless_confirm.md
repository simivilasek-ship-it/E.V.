Krátký popis:
Tento PR zpřísňuje chování potvrzovacích dialogů v headless (server) režimu. Do té doby Jarvis v headless módu automaticky schvaloval ELEVATED akce (např. delete_file, shutdown), což je potenciální bezpečnostní riziko při nasazení na serverech. Po změně jsou ELEVATED akce v headless režimu výchozí zamítnuty.

Co měním:
- security_v2.py: confirm_action nyní v headless režimu implicitně zamítá ELEVATED akce.
- Přidána podpora env var JARVIS_HEADLESS_APPROVE_ELEVATED (hodnoty: 1/true/yes), která povolí staré chování pouze pokud je explicitně nastavená.
- README.md: přidána sekce v Troubleshooting popisující nové chování a varování ohledně env var.
- Přidány unit testy tests/test_confirm_action_headless.py pokrývající nové chování.

Důvod:
Prevence nechtěného vykonání kritických systémových akcí při headless nasazení.

Bezpečnostní dopad:
Zpřísnění — bezpečnější výchozí chování.
Pokud někdo spoléhá na staré auto-approve chování v headless (např. CI/dev), musí explicitně nastavit JARVIS_HEADLESS_APPROVE_ELEVATED=1.

Testy:
Přidány unit testy pro validaci nového chování. Doporučuji spustit celou sadu testů (pytest) před mergem.

Migrace / Konfigurace:
Pro zachování starého chování ve controlled prostředí: export JARVIS_HEADLESS_APPROVE_ELEVATED=1
Poznámka: nepovolujte na veřejných serverech.

Files changed:
- security_v2.py
- README.md
- tests/test_confirm_action_headless.py
