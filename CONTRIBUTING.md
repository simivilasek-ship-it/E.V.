# Přispívání do JARVIS

## Jak přidat nový příkaz

### 1. Trigger v `local_router.py`
```python
m = re.search(r"\b(muj|prikaz)\s+(.+)", t)
if m:
    return "Provádím.", {"action": "muj_prikaz", "params": {"arg": m.group(2)}}
```

### 2. Implementace v `commands/`
```python
def cmd_muj_prikaz(arg: str) -> str:
    return f"Hotovo: {arg}"
```

### 3. Export z `commands/__init__.py`
```python
from .system import cmd_muj_prikaz
# v CommandExecutor:
def _cmd_muj_prikaz(self, arg="", **_): return cmd_muj_prikaz(arg)
```

### 4. Oprávnění v `security_v2.py`
```python
"muj_prikaz": PermissionLevel.SAFE,
```

### 5. Test
```python
def test_muj_prikaz():
    assert "test" in cmd_muj_prikaz("test")
```

## Jak přidat plugin
Viz [README.md → Plugin systém](README.md#plugin-systém--15-skills)

## Spuštění testů
```bash
source ~/Stažené/jarvis-env/bin/activate
python -m pytest tests/ test_jarvis.py -v
```

## Linter
```bash
ruff check . --select F,E7
```

## Pull Request checklist
- [ ] Testy prochází (`python -m pytest`)
- [ ] Ruff clean (`ruff check .`)
- [ ] README aktualizováno pokud se mění API
- [ ] Nové příkazy mají trigger + test + security permission
