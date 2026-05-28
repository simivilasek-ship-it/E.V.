# JARVIS v4.3 — Docker image
# Headless mód: pouze dashboard + LLM backend, bez GUI
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev espeak-ng ffmpeg curl \
    tesseract-ocr tesseract-ocr-ces \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 jarvis
WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir fastapi uvicorn rapidfuzz

COPY --chown=jarvis:jarvis . .

USER jarvis
EXPOSE 8002

# Výchozí: dashboard + headless backend (bez Tkinter GUI)
CMD ["python", "-c", "import dashboard; dashboard.run_dashboard()"]
