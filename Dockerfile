# JARVIS v5.12.0 — Headless Docker image
# Spustí FastAPI backend (port 8002) + React web UI (/app)
# Bez Tkinter GUI, bez zvuku — vhodné pro server/NAS/cloud

FROM python:3.11-slim

# Systémové závislosti
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget ffmpeg portaudio19-dev espeak-ng \
    tesseract-ocr tesseract-ocr-ces \
    nodejs npm \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 jarvis
WORKDIR /app

# Python závislosti
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir fastapi uvicorn rapidfuzz sentence-transformers

# React build
COPY web/package*.json web/
RUN cd web && npm ci --legacy-peer-deps --quiet
COPY web/ web/
RUN cd web && npm run build && mv out ../web_dist && cd .. && rm -rf web/node_modules

# Zdrojový kód
COPY --chown=jarvis:jarvis . .

# Ollama konfigurace
ENV OLLAMA_HOST=http://ollama:11434
ENV JARVIS_HEADLESS=1

USER jarvis
EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD curl -f http://localhost:8002/health || exit 1

# Headless mód: jen backend + web UI
CMD ["python", "dashboard.py"]
