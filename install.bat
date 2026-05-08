@echo off
chcp 65001 >nul
echo ============================================
echo   JARVIS v2.0 — Instalace (Windows)
echo ============================================
echo.

echo [1/4] Aktualizuji pip...
python -m pip install --upgrade pip --quiet

echo [2/4] Instaluji povinne zavislosti...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo CHYBA: Instalace selhala. Zkus spustit jako Administrator.
    pause & exit /b 1
)

echo [3/4] Instaluji volitelne zavislosti (pycaw - presna hlasitost)...
pip install pycaw comtypes --quiet
if %errorlevel% neq 0 (
    echo INFO: pycaw se nepodarilo nainstalovat — hlasitost pujde nastavit i bez ni.
)

echo [4/4] Kontroluji Ollama...
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ============================================
    echo   POZOR: Ollama neni nainstalovana!
    echo   Stahni z: https://ollama.com/download
    echo   Po instalaci spust: ollama pull llama3.1:8b
    echo ============================================
) else (
    echo Ollama nalezena. Stahuji model llama3.1:8b...
    ollama pull llama3.1:8b
    echo Model stazeny.
)

echo.
echo ============================================
echo   Hotovo! Spust JARVIS prikazy:
echo     1. ollama serve
echo     2. python jarvis.py
echo ============================================
pause
