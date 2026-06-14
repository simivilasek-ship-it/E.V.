.PHONY: start install update stop logs help release test test-front

# Výchozí cíl
help:
	@echo ""
	@echo "  JARVIS — příkazy"
	@echo ""
	@echo "  make start    — spustit JARVIS (nainstaluje vše pokud chybí)"
	@echo "  make install  — pouze instalace"
	@echo "  make update   — git pull + reinstall závislostí"
	@echo "  make stop     — zastavit běžící server"
	@echo "  make logs     — zobrazit dnešní work log"
	@echo "  make docker   — spustit přes Docker Compose
  make test     — spustit Python testy (pytest)
  make test-front — spustit frontend testy (Vitest)
  make release  — tag + push + GitHub Release"
	@echo ""

start:
	@bash start.sh

install:
	@bash install.sh

update:
	git pull
	source venv/bin/activate && pip install -r requirements.txt --quiet
	@echo "  ✓ Aktualizováno — spusť: make start"

stop:
	@source venv/bin/activate && python3 dashboard.py --restart 2>/dev/null || \
	 pkill -f "dashboard.py" 2>/dev/null || echo "  Žádný běžící server nenalezen."

logs:
	@source venv/bin/activate && python3 jarvis.py log --today

docker:
	docker compose up

test:
	source venv/bin/activate && pytest tests/ -x -q --tb=short

test-front:
	cd web && npm run test:unit -- --run

release:
	@VERSION=$$(python3 -c "import sys; sys.path.insert(0,'.'); from config import __version__; print(__version__)"); \
	echo "Releasing v$$VERSION..."; \
	git add -A && git commit -m "chore: release v$$VERSION" || true; \
	git tag "v$$VERSION" 2>/dev/null || echo "Tag already exists"; \
	git push origin main --tags; \
	gh release create "v$$VERSION" \
	  --title "JARVIS v$$VERSION" \
	  --notes-file <(grep -A 50 "\[$$VERSION\]" CHANGELOG.md | head -51) \
	  2>/dev/null && echo "  ✓ GitHub Release v$$VERSION vytvořen" || \
	  echo "  GitHub Release: run 'gh release create v$$VERSION' manually"
