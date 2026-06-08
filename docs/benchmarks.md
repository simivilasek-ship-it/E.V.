# JARVIS v5.9 — Benchmarky

Měřeno na: **Intel i7, 30 GB RAM, Ubuntu 24.04 LTS**  
Datum: 2026-06-03 · Branch: security/headless-confirm-fix

---

## Latence odpovědí

### LocalRouter (regex matching)

```
1 000 dotazů "otevři chrome"  →  4.4 ms celkem  =  0.004 ms / dotaz
```

LocalRouter nikdy nevolá LLM — čistý regex, O(n) přes pravidla.

### LLM odpovědi — Ollama lokálně

Měřeno na `qwen2.5:3b` (výchozí model), 3 runs:

| Run | Latence | Tokeny | Tok/s |
|-----|---------|--------|-------|
| 1 (cold start) | 1 473 ms | 4 | — |
| 2 (warm) | 122 ms | 5 | — |
| 3 (warm) | 113 ms | 5 | — |
| **Průměr warm** | **~117 ms** | | |
| **Delší odpověď (100 tok)** | **~1 189 ms** | 100 | **~84 tok/s** |

> Cold start zahrnuje načtení modelu do RAM (~1.4s). Warm odpovědi jsou výrazně rychlejší.

### LLM odpovědi — Groq cloud

| Model | Latence | Tok/s | Použití |
|-------|---------|--------|---------|
| `llama-3.1-8b-instant` | ~150 ms | ~500 | Chat, překlady |
| `llama-3.3-70b-versatile` | ~250 ms | ~200 | Kód, reasoning |
| `llama-3.2-90b-vision` | ~400 ms | ~150 | Vision analýza |
| `whisper-large-v3` (STT) | ~200 ms | — | Transkripce |

*Groq API je zdarma s limity: 14 400 požadavků/den, 500 000 tokenů/den.*

### End-to-end latence (hlas → odpověď)

```
Mluvím (utterance)
    │  WebRTC VAD detekuje konec řeči          ~30 ms
    ▼
Groq Whisper transkripce                      ~200 ms
    ▼
LocalRouter / LLM routing                     < 1 ms
    ▼
Groq LLaMA 3.3 (první token)                 ~150 ms
    ▼
Edge-TTS (první věta začne hrát)             ~200 ms
─────────────────────────────────────────────────────
Celkem od konce věty po začátek odpovědi:   ~580 ms
```

---

## Spotřeba paměti

### Python proces

| Stav | RAM |
|------|-----|
| Idle (bez Ollama) | **34 MB** |
| Po prvním LLM dotazu | **+80 MB** (inicializace memory, graph) |
| Plný běh (všechny systémy) | **~350 MB** |

### Ollama modely

| Model | RAM | VRAM (GPU) |
|-------|-----|-----------|
| `qwen2.5:3b` | **+268 MB** | ~2.0 GB |
| `qwen2.5:1.5b` | +180 MB | ~1.1 GB |
| `llama3.1:8b` | +550 MB | ~5.5 GB |
| `llava:7b` (vision) | +450 MB | ~4.5 GB |
| LLaVA po použití (`keep_alive=0`) | 0 MB | **0 GB** ← uvolní se |

### Celková spotřeba

| Konfigurace | RAM | VRAM |
|------------|-----|------|
| Minimální (qwen2.5:3b, bez GPU) | ~650 MB | 0 GB |
| Doporučená (qwen2.5:3b, s GPU) | ~650 MB | ~2.5 GB |
| Plná (llama3.1:8b + LLaVA) | ~1.3 GB | ~10 GB |

---

## Rychlost agentů

### ReAct Agent — typické úkoly

| Úkol | Kroky | Model | Čas |
|------|-------|-------|-----|
| "Najdi TODO v projektu (grep)" | 2 | Groq 8B | ~3 s |
| "Napiš Python fibonacci funkci" | 3 | Groq 70B | ~8 s |
| "Shrň obsah souboru README.md" | 2 | Groq 8B | ~4 s |
| "Spusť testy a oprav chyby" | 5–8 | Groq 70B | ~25 s |

### Graph Agent (planner → executor → critic)

| Úkol | Kroky | Čas |
|------|-------|-----|
| Jednoduchý 2-krokový úkol | 2+overhead | ~6 s |
| Složitý úkol s přeplánováním | 6–8 | ~30 s |

### Vision Computer Use

| Operace | Metoda | Latence |
|---------|--------|---------|
| Najdi a klikni na tlačítko | OCR (pytesseract) | **~50 ms** |
| Najdi element který OCR nenajde | Groq Vision | **~400 ms** |
| Pořídí screenshot | pyautogui | ~20 ms |
| run_task() — 5 kroků | mix | ~8 s |

---

## Cache efektivita

### LLM Cache (`_LLMCache`)

- Opakovaný identický dotaz: **< 1 ms** (cache hit)
- TTL: 10 minut
- Kapacita: 200 záznamů (LRU eviction)
- Automaticky přeskakuje real-time dotazy (počasí, čas, kurzy)

### OCR Cache

- Identický screenshot (SHA1): **< 1 ms**
- Uloží na disk, přežije restart

### Ollama prompt cache (Llama.cpp)

- Sdílený kontext history v jednom `/api/chat` volání
- Parciální re-compute pouze pro nové tokeny
- Efektivní pro opakované ReAct kroky se stejnou historií

---

## Srovnání konfigurací

| | Minimální | Doporučená | High-end |
|-|-----------|-----------|---------|
| **Model** | qwen2.5:3b | qwen2.5:3b + Groq | llama3.1:8b + Groq |
| **RAM** | 4 GB | 8 GB | 16 GB |
| **GPU** | Není potřeba | Volitelné | Doporučeno |
| **STT latence** | ~2 s (Vosk) | **~200 ms** (Groq) | ~200 ms |
| **LLM latence** | ~1 s | **~200 ms** | ~200 ms |
| **Vision** | ❌ | OCR pouze | OCR + LLaVA |
| **Soukromí** | ✅ 100% lokální | 🔄 Hybridní | 🔄 Hybridní |

---

## Jak zreplikovat benchmarky

```bash
cd Jarvis
python3 -c "
import time, requests, psutil

url = 'http://localhost:11434/api/chat'
msgs = [{'role':'user','content':'Odpověz jedním slovem: Ahoj'}]

# Warmup
requests.post(url, json={'model':'qwen2.5:3b','messages':msgs,'stream':False,'options':{'num_predict':5}})

# Measure 5x
for i in range(5):
    t0 = time.monotonic()
    r = requests.post(url, json={'model':'qwen2.5:3b','messages':msgs,'stream':False,'options':{'num_predict':20}})
    ms = (time.monotonic()-t0)*1000
    tok = r.json().get('eval_count', 0)
    print(f'Run {i+1}: {ms:.0f}ms, {tok} tokens, {tok/(ms/1000):.0f} tok/s')

# RAM
import os; proc = psutil.Process(os.getpid())
print(f'RAM: {proc.memory_info().rss/1024**2:.0f} MB')
"
```
