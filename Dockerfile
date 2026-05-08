# JARVIS v2.0 — Docker kontejner
FROM python:3.11-slim

# Nainstaluj systémové závislosti
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    espeak-ng \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Vytvoř uživatele
RUN useradd -m jarvis

# Nastav pracovní adresář
WORKDIR /app

# Zkopíruj závislosti
COPY requirements.txt .

# Nainstaluj Python závislosti
RUN pip install --no-cache-dir -r requirements.txt

# Zkopíruj aplikaci
COPY . .

# Nastav vlastnictví
RUN chown -R jarvis:jarvis /app

# Přepni na uživatele
USER jarvis

# Expose port pro Ollama (pokud by běžel v kontejneru)
EXPOSE 11434

# Spusť JARVIS
CMD ["python", "jarvis.py"]