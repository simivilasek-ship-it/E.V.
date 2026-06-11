.PHONY: start install update stop logs help

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
	@echo "  make docker   — spustit přes Docker Compose"
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
