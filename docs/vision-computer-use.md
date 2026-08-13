# Vision a Computer Use

E.V. umí vidět obrazovku a ovládat počítač jako člověk — klikat na tlačítka, vyplňovat formuláře, číst obsah aplikací.

---

## Přehled vrstev

```
Uživatel: "Najdi na Slacku zprávu od Petra a odpověz mu"
       │
       ▼
VisionAgent.run_task(task)       ← high-level orchestrátor
       │
       ├── 1. Pořídí screenshot
       ├── 2. Plán kroků přes LLM (Groq/Ollama)
       │         [open_url(Slack), click("Petr"), type("Odpověď"), press(enter)]
       │
       └── 3. Provede kroky:
             ├── smart_click("Petr") → VisionOCRPipeline (OCR, ~50ms)
             │                      → LLaVA fallback (~2s) pokud OCR nenajde
             └── type_text("...") → pyautogui.typewrite()
```

---

## VisionOCRPipeline (`vision_v2.py`)

Analyzuje screenshot a vrátí strukturovaná data o obrazovce.

### Vstup → Výstup

```python
from vision_v2 import VisionOCRPipeline

pipeline = VisionOCRPipeline()
result = pipeline.analyze()  # pořídí screenshot automaticky
# nebo:
result = pipeline.analyze("/tmp/screen.png")

print(result.ocr_text)
# "Visual Studio Code  File  Edit  Selection..."

print(result.active_app)
# "code"

for el in result.ui_elements:
    print(f"{el.role}: {el.name!r} @ ({el.bbox[0]}, {el.bbox[1]})")
# button: "File" @ (42, 28)
# button: "Edit" @ (89, 28)
# input:  "" @ (400, 28)
# label:  "EXPLORER" @ (12, 80)
```

### Klasifikace UI elementů

| Třída | Kritéria detekce |
|-------|-----------------|
| `button` | Obdélník < 200×50px s textem uvnitř |
| `input` | Obdélník > 100px šířky bez výrazného textu |
| `label` | Text bez ohraničujícího obdélníku |

Detekce probíhá přes OpenCV (`findContours` + `approxPolyDP`).

### Závislosti

```bash
pip install pytesseract opencv-python pyautogui pillow
# Systémově:
sudo apt install tesseract-ocr tesseract-ocr-ces  # + český jazyk
```

Bez závislostí: `pipeline.available == False`, metody vrátí prázdný výsledek.

---

## VisualActionPlanner (`vision_v2.py`)

Najde element na obrazovce podle textového popisu a vrátí souřadnice.

### Strategie hledání

```
Instrukce: "tlačítko Přihlásit"
       │
       ▼
1. OCR screenshot → seznam slov s bounding boxy
       │
       ▼
2. Fuzzy match instrukce vs. OCR slova (Jaccard tokenový overlap)
       │
   ┌───┴──────────────────────────────────────┐
   │ skóre > 0.4?                             │ skóre < 0.4
   ▼ ANO                                      ▼ NE
Vrátí (x, y) středu                  LLaVA/Groq vision fallback
matching slova                              │
                                            ▼
                                   JSON: {found, x, y, popis}
```

### Příklad

```python
from vision_v2 import get_planner

planner = get_planner()
result = planner.find_and_click("Přihlásit se")

if result.found:
    print(f"Nalezeno: '{result.matched_text}' @ ({result.x}, {result.y})")
    print(f"Metoda: {result.method}")  # "ocr" nebo "vision"
else:
    print(f"Nenalezeno: {result.error}")
```

---

## VisionAgent (`vision_computer_use.py`)

High-level agent pro komplexní UI interakce.

### Základní operace

```python
from vision_computer_use import get_vision_agent

agent = get_vision_agent()

# Kliknutí (OCR-first, vision fallback)
result = agent.smart_click("tlačítko Přihlásit")
# nebo: agent.click("Přihlásit")  ← jen vision, pomalejší

# Napsání textu
agent.type_text("jan.novak@email.cz")

# Najdi pole a vyplň (click + clear + type)
agent.find_and_fill("pole E-mail", "jan.novak@email.cz")
agent.find_and_fill("pole Heslo",  "tajné123")

# Stisk klávesy
agent.press_key("enter")
agent.press_key("tab")
agent.press_key("escape")

# Scrollování
agent.scroll("dolů", clicks=3)
agent.scroll("nahoru", clicks=5)

# Otevření URL
agent.open_url_in_browser("https://gmail.com")
```

### Autonomní úkol (ReAct smyčka)

```python
result = agent.run_task(
    "Otevři Gmail, najdi e-mail s předmětem 'Faktura', "
    "stáhni přílohu a ulož na plochu",
    max_steps=10
)
print(result)
# "Dokončeno 7/7 kroků pro úkol: 'Otevři Gmail...'
#   1. open_url(gmail.com) — ✓
#   2. click(vyhledávací pole) — ✓
#   3. type(Faktura) — ✓
#   4. press(enter) — ✓
#   5. click(první výsledek) — ✓
#   6. click(příloha) — ✓
#   7. click(Stáhnout) — ✓"
```

### Jak `run_task()` funguje

1. Pořídí screenshot aktuálního stavu
2. Pošle screenshot + popis úkolu do Groq/Ollama → JSON plán akcí
3. Provede každou akci (click/type/scroll/open_url)
4. Čeká 0.8s mezi akcemi (DOM stabilizace)
5. Vrátí výsledek každého kroku

---

## RealTimeScreenMonitor (`vision_v2.py`)

Zachycuje obrazovku v reálném čase a detekuje změny.

### Použití

```python
from vision_v2 import RealTimeScreenMonitor

monitor = RealTimeScreenMonitor(
    fps=1,              # snímky za sekundu (default 1)
    threshold=0.02,     # 2% pixelů musí být změněno pro trigger
)

def on_screen_change(event):
    print(f"Změna detekována v regionu: {event.region}")
    print(f"Diff: {event.diff_percent:.1%} pixelů")

monitor.start(on_change=on_screen_change)

# ... E.V. běží ...

monitor.stop()
```

### ChangeEvent struktura

```python
@dataclass
class ChangeEvent:
    region: tuple      # (x, y, width, height) nebo None pro celou obrazovku
    diff_percent: float  # procento změněných pixelů (0.0–1.0)
    screenshot_path: str  # cesta k aktuálnímu screenshotu
    timestamp: float
```

### Integrace s Proactive Engine

RealTimeScreenMonitor je propojen s Proactive Engine — pokud se otevře nový soubor ve VS Code, E.V. automaticky zkontroluje TODO/FIXME komentáře.

---

## Computer Use Backend (`computer_use.py`)

Accessibility-based UI automation (alternativa k vision approach).

| Backend | Platforma | Závislost |
|---------|-----------|-----------|
| `LinuxATSPIBackend` | Linux | `pyatspi` |
| `WindowsUIABackend` | Windows | `uiautomation` |
| `MacOSAXBackend` | macOS | `PyObjC` |

Accessibility backend je rychlejší a přesnější než vision (nepotřebuje OCR), ale funguje jen u aplikací s AT-SPI/UIA podporou.

```python
from computer_use import get_ui_backend, ui_click, ui_tree

# Zobrazí strom UI elementů aktivního okna
print(ui_tree())

# Klikne na element dle textu + role
result = ui_click("Přihlásit", role="push button")
print(result)  # "ok" nebo chybová zpráva
```

### Nastavení

```json
{
  "computer_use_enabled": true,
  "computer_use_backend": "auto"
}
```

---

## Srovnání přístupů

| Kritérium | Accessibility (AT-SPI) | OCR (pytesseract) | Vision (LLaVA) |
|-----------|----------------------|-------------------|----------------|
| Rychlost | ⚡ < 10 ms | 🟡 200–500 ms | 🔴 2–5 s |
| Přesnost | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Závislosti | pyatspi/UIA | pytesseract + OpenCV | Ollama + LLaVA model |
| Rozsah | AT-SPI aplikace | Vše co je na obrazovce | Vše co je na obrazovce |
| Funguje offline | ✅ | ✅ | ✅ (lokální LLaVA) |

**Doporučená strategie (smart_click):**
1. Zkus OCR (~50 ms) → nejrychlejší
2. Fallback na vision (~2 s) → universal
3. Fallback na accessibility (pokud dostupný) → nejpřesnější

---

## Tipy pro spolehlivé UI automation

1. **Čekej na DOM stabilizaci** — po kliknutí počkej 0.5–1s před dalším krokem
2. **Popis elementu buď specifický** — `"tlačítko Odeslat formulář"` > `"tlačítko"`
3. **Fallback strategie** — vždy mej `try/except` a alternativní cestu
4. **Test v izolaci** — testuj jednotlivé akce před `run_task()`
5. **VRAM** — LLaVA se automaticky uvolní z VRAM po každém vision volání (`keep_alive=0`)
