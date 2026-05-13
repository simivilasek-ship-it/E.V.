#!/bin/bash
cd "/home/simi/Stažené/nepojmenovaná složka"

git commit -m "v3.0: Kompletní refaktoring a vylepšení

- Nový config systém s .env supportem (python-dotenv)
- Structured logging s loguru (JSON formát)
- Vylepšený commands.py s type hints a lepší architekturou
- Nové moduly: cache_manager, health_check, offline_mode
- Rozšířené testy (50+ testů) s pytest
- Security 2.0: audit log, permission levels, dangerous pattern detection
- Plugin system s hot-reload supportem
- Neural memory systém s decay a auto-maintenance
- Opraveny duplicity v commands.py
- Přidán .env.example pro snadnou konfiguraci
- Updated README s developer dokumentací"

echo "Commit exit code: $?"
git push origin main
echo "Push exit code: $?"