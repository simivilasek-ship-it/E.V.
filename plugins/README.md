# JARVIS Plugins

Každý plugin = složka s těmito soubory:
- `plugin.py` — implementace
- `metadata.json` — popis, verze, oprávnění

## Příklad metadata.json
```json
{
  "name": "my_plugin",
  "version": "1.0",
  "description": "Popis pluginu",
  "commands": ["my_command"],
  "permission_level": "safe"
}
```

## Příklad plugin.py
```python
def register(jarvis):
    jarvis.register_command("my_command", my_handler)

def my_handler(param1, param2="default"):
    return f"Výsledek: {param1}"
```
