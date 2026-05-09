"""
JARVIS GUI — Animovaný hlasový asistent
Samostatný GUI modul s Three.js-inspirovaným orbem na tkinter Canvas.
Barvy: fialová/modrá paleta (bez zlata/oranžové)
"""

import math
import random
import tkinter as tk
import customtkinter as ctk
from datetime import datetime


# ══════════════════════════════════════════════════════
#  BARVY
# ══════════════════════════════════════════════════════

BG      = "#080810"   # hlavní pozadí — tmavá modročerná
BG2     = "#0e0e1c"   # sekundární pozadí
BG3     = "#14142a"   # terciární (bubliny, vstupy)
FG      = "#f1f5f9"   # primární text
MUTED   = "#475569"   # tlumený text
BORDER  = "#1e1b4b"   # rámeček

# Barvy ORBu pro každý stav
ORB_COLORS = {
    "idle":      "#8b5cf6",   # fialová
    "listening": "#ef4444",   # červená
    "thinking":  "#3b82f6",   # modrá
    "speaking":  "#10b981",   # smaragdová
}

# Tmavší verze pro glow efekt (nižší opacita = ztmavení)
ORB_DARK = {
    "idle":      "#4c1d95",
    "listening": "#7f1d1d",
    "thinking":  "#1e3a8a",
    "speaking":  "#064e3b",
}

STATE_LABELS = {
    "idle":      "I D L E",
    "listening": "L I S T E N I N G",
    "thinking":  "T H I N K I N G",
    "speaking":  "S P E A K I N G",
}


# ══════════════════════════════════════════════════════
#  POMOCNÉ FUNKCE
# ══════════════════════════════════════════════════════

def blend(color_hex: str, bg_hex: str, alpha: float) -> str:
    """Smíchá barvu s pozadím při dané průhlednosti (0–1)."""
    def parse(h):
        h = h.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    cr, cg, cb = parse(color_hex)
    br, bg_, bb = parse(bg_hex)
    r = int(br + (cr - br) * alpha)
    g = int(bg_ + (cg - bg_) * alpha)
    b = int(bb + (cb - bb) * alpha)
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_lerp(a: str, b: str, t: float) -> str:
    """Lineární interpolace mezi dvěma hexadecimálními barvami."""
    return blend(b, a, t)


# ══════════════════════════════════════════════════════
#  ČÁSTICE
# ══════════════════════════════════════════════════════

class Particle:
    """Jedna částice pohybující se po eliptické dráze kolem středu orbu."""

    def __init__(self, cx: float, cy: float):
        self.cx = cx
        self.cy = cy
        self.orbit_r  = random.uniform(55, 125)   # poloměr dráhy
        self.phase    = random.uniform(0, 2 * math.pi)
        self.speed    = random.uniform(0.008, 0.035)
        # Naklopení elipsy (simulace 3D sféry)
        self.tilt     = random.uniform(0.15, 0.85)
        self.tilt_dir = random.choice([-1, 1])
        # Rotace celé dráhy kolem osy Y
        self.axis     = random.uniform(0, math.pi)
        # Vizuální vlastnosti
        self.size     = random.uniform(1.5, 3.5)
        # Z-hloubka určí, zda je částice "před" nebo "za" orbem
        self.z_phase  = random.uniform(0, 2 * math.pi)
        self.z_speed  = self.speed * random.uniform(0.5, 1.5)

    def position(self, frame: int):
        """Vrátí (x, y, z) pozici částice v daném snímku."""
        angle = self.phase + self.speed * frame

        # 3D eliptická dráha
        x3 = self.orbit_r * math.cos(angle)
        y3 = self.orbit_r * math.sin(angle) * self.tilt
        z3 = self.orbit_r * math.sin(angle) * (1 - self.tilt) * self.tilt_dir

        # Projekce do 2D (axonometrická rotace)
        cos_a = math.cos(self.axis)
        sin_a = math.sin(self.axis)
        x2 = x3 * cos_a - z3 * sin_a
        y2 = y3
        z2 = x3 * sin_a + z3 * cos_a   # hloubka pro velikost/jas

        return self.cx + x2, self.cy + y2, z2


# ══════════════════════════════════════════════════════
#  ORB CANVAS
# ══════════════════════════════════════════════════════

class OrbCanvas(tk.Canvas):
    """
    Animovaný orb kreslený na tkinter Canvas každých 30 ms.
    Obsahuje částice, vnitřní glow, vnější ring s tečkami a stavový text.
    """

    ORB_SIZE = 300   # velikost canvasu

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            width=self.ORB_SIZE,
            height=self.ORB_SIZE,
            bg=BG,
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self.cx = self.ORB_SIZE / 2
        self.cy = self.ORB_SIZE / 2

        # Stav
        self._state       = "idle"
        self._color       = ORB_COLORS["idle"]
        self._target_color = self._color
        self._lerp_t      = 0.0

        # Animace
        self._frame       = 0
        self._pulse       = 0.0
        self._ring_angle  = 0.0
        self._running     = True

        # Částice
        self._particles   = [Particle(self.cx, self.cy) for _ in range(60)]

        # Spusť animaci
        self._animate()

    # ── STAV ─────────────────────────────────────────

    def set_state(self, state: str):
        if state not in ORB_COLORS:
            return
        self._state        = state
        self._target_color = ORB_COLORS[state]
        self._lerp_t       = 0.0

    # ── ANIMACE ──────────────────────────────────────

    def stop(self):
        self._running = False

    def _animate(self):
        if not self._running:
            return

        self._frame     += 1
        self._pulse     += 0.04
        self._ring_angle = (self._ring_angle + 1.2) % 360

        # Plynulý přechod barvy
        if self._lerp_t < 1.0:
            self._lerp_t = min(1.0, self._lerp_t + 0.04)
            self._color  = hex_lerp(self._color, self._target_color, self._lerp_t)

        self._draw()
        self.after(30, self._animate)

    def _draw(self):
        self.delete("all")

        # 1. Glow core — 4 soustředné kruhy s klesající opacitou
        self._draw_glow()

        # 2. Částice
        self._draw_particles()

        # 3. Vnější rotující ring s tečkami
        self._draw_ring()

    def _draw_glow(self):
        """Kreslí pulsující vnitřní záři (4 vrstvy)."""
        pulse = math.sin(self._pulse) * 8
        layers = [
            (35 + pulse * 0.5, 0.42),
            (50 + pulse * 0.6, 0.26),
            (65 + pulse * 0.7, 0.15),
            (80 + pulse,       0.08),
        ]
        for r, alpha in layers:
            c = blend(self._color, BG, alpha)
            self.create_oval(
                self.cx - r, self.cy - r,
                self.cx + r, self.cy + r,
                fill=c, outline="",
            )

        # Střed — nejjasnější tečka
        r_core = 12 + math.sin(self._pulse) * 2
        c_core = blend(self._color, "#ffffff", 0.3)
        self.create_oval(
            self.cx - r_core, self.cy - r_core,
            self.cx + r_core, self.cy + r_core,
            fill=c_core, outline="",
        )

    def _draw_particles(self):
        """Kreslí 60 částic na eliptických drahách."""
        # Rychlost závisí na stavu
        speed_mult = {
            "idle":      1.0,
            "listening": 1.4,
            "thinking":  2.2,
            "speaking":  1.7,
        }.get(self._state, 1.0)

        for p in self._particles:
            # Uloží původní rychlost, modifikuje dočasně
            orig = p.speed
            p.speed = orig * speed_mult
            x, y, z = p.position(self._frame)
            p.speed = orig

            # Z-hloubka → velikost a jas (simulace 3D)
            z_norm   = (z / 130 + 1) / 2          # 0–1, 0 = vzadu, 1 = vpředu
            size     = p.size * (0.4 + z_norm * 0.6)
            alpha    = 0.15 + z_norm * 0.75

            # Částice za centrem — tmavší
            if z_norm < 0.35:
                alpha *= 0.5
                c = blend(ORB_DARK[self._state], BG, alpha)
            else:
                c = blend(self._color, BG, alpha)

            if 0 < x < self.ORB_SIZE and 0 < y < self.ORB_SIZE:
                self.create_oval(
                    x - size, y - size,
                    x + size, y + size,
                    fill=c, outline="",
                )

    def _draw_ring(self):
        """Kreslí vnější tenký ring (1px) s rotujícími tečkami."""
        r    = 105
        c    = blend(self._color, BG, 0.35)
        # Celý kruh jako polygonový aproximace
        self.create_oval(
            self.cx - r, self.cy - r,
            self.cx + r, self.cy + r,
            outline=c, width=1, fill="",
        )

        # 4 tečky rovnoměrně rozmístěné, rotující
        dot_r = 3
        dot_c = blend(self._color, BG, 0.85)
        for i in range(4):
            angle_deg = self._ring_angle + i * 90
            angle_rad = math.radians(angle_deg)
            dx = r * math.cos(angle_rad)
            dy = r * math.sin(angle_rad)
            self.create_oval(
                self.cx + dx - dot_r, self.cy + dy - dot_r,
                self.cx + dx + dot_r, self.cy + dy + dot_r,
                fill=dot_c, outline="",
            )


# ══════════════════════════════════════════════════════
#  CHAT BUBLINA
# ══════════════════════════════════════════════════════

class ChatBubble(ctk.CTkFrame):
    """Jedna chatová bublina (user vpravo, jarvis vlevo)."""

    def __init__(self, parent, text: str, sender: str, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        is_user = sender == "user"
        ts      = datetime.now().strftime("%H:%M")

        # Meta řádek (emoji + čas)
        meta = ctk.CTkFrame(self, fg_color="transparent")
        meta.pack(fill="x")

        if is_user:
            ctk.CTkLabel(meta, text=ts,    font=("DM Sans", 9),  text_color=MUTED).pack(side="right", padx=(0, 2))
            ctk.CTkLabel(meta, text="🧑",  font=("DM Sans", 10), text_color=FG).pack(side="right")
        else:
            ctk.CTkLabel(meta, text="🤖",  font=("DM Sans", 10), text_color=ORB_COLORS["thinking"]).pack(side="left")
            ctk.CTkLabel(meta, text=ts,    font=("DM Sans", 9),  text_color=MUTED).pack(side="left", padx=(2, 0))

        # Textová bublina
        bubble_bg  = "#16162a" if not is_user else "#1a1a3a"
        border_col = ORB_COLORS["thinking"] if not is_user else ORB_COLORS["idle"]

        bubble = ctk.CTkFrame(
            self,
            fg_color=bubble_bg,
            border_color=border_col,
            border_width=1,
            corner_radius=12,
        )
        bubble.pack(
            anchor="e" if is_user else "w",
            padx=(40, 4) if is_user else (4, 40),
            pady=(2, 0),
        )

        ctk.CTkLabel(
            bubble,
            text=text,
            font=("DM Sans", 12),
            text_color=FG,
            wraplength=220,
            justify="right" if is_user else "left",
        ).pack(padx=10, pady=6)


# ══════════════════════════════════════════════════════
#  HLAVNÍ GUI
# ══════════════════════════════════════════════════════

class JarvisGUI:
    """
    Hlavní GUI třída JARVIS asistenta.

    Veřejné API:
      set_state(state)          — změní stav orbu
      add_message(text, sender) — přidá zprávu do chatu
      set_status(text)          — nastaví text pod orbem
      run()                     — spustí mainloop
      on_mic_click              — callback pro klik na mikrofon
      on_send                   — callback pro odeslání textu
    """

    def __init__(self):
        # Callbacky (nastaví volající kód)
        self.on_mic_click: callable = None
        self.on_send:      callable = None

        self._chat_open  = False
        self._dark_mode  = True
        self._state      = "idle"

        self._setup_window()
        self._build_ui()

    # ── OKNO ─────────────────────────────────────────

    def _setup_window(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.root = ctk.CTk()
        self.root.title("JARVIS")
        self.root.geometry("480x700")
        self.root.resizable(False, False)
        self.root.configure(fg_color=BG)

        # Vystředění okna
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x  = (sw - 480) // 2
        y  = (sh - 700) // 2
        self.root.geometry(f"480x700+{x}+{y}")

        # Mezerník = mikrofon
        self.root.bind("<space>", self._on_space)

    # ── SESTAVENÍ UI ─────────────────────────────────

    def _build_ui(self):
        # ── Header ──────────────────────────────────
        self._build_header()

        # ── ORB sekce ───────────────────────────────
        self._orb_section = ctk.CTkFrame(self.root, fg_color=BG, corner_radius=0)
        self._orb_section.pack(fill="both", expand=True)

        # Canvas orbu — vystředěný
        canvas_wrap = ctk.CTkFrame(self._orb_section, fg_color=BG, corner_radius=0)
        canvas_wrap.pack(expand=True)

        self.orb = OrbCanvas(canvas_wrap)
        self.orb.pack()

        # Stavový text pod orbem (s mezerami = letter-spacing efekt)
        self._status_lbl = ctk.CTkLabel(
            canvas_wrap,
            text="I D L E",
            font=("Courier New", 11),
            text_color=ORB_COLORS["idle"],
        )
        self._status_lbl.pack(pady=(8, 0))

        # Doplňkový status text (set_status)
        self._info_lbl = ctk.CTkLabel(
            canvas_wrap,
            text="",
            font=("DM Sans", 11),
            text_color=MUTED,
        )
        self._info_lbl.pack(pady=(2, 0))

        # ── Chat panel (skrytý ve výchozím stavu) ────
        self._build_chat_panel()

        # ── Dolní ovládání ───────────────────────────
        self._build_controls()

    def _build_header(self):
        """Tenký header s názvem a hodinami."""
        hdr = ctk.CTkFrame(self.root, fg_color=BG2, corner_radius=0, height=42)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr,
            text="J A R V I S",
            font=("Courier New", 14),
            text_color=ORB_COLORS["idle"],
        ).pack(side="left", padx=18)

        self._clock_lbl = ctk.CTkLabel(
            hdr, text="",
            font=("Courier New", 11),
            text_color=MUTED,
        )
        self._clock_lbl.pack(side="right", padx=16)

        # Dělicí čára
        ctk.CTkFrame(self.root, fg_color=BORDER, height=1, corner_radius=0).pack(fill="x")

        self._tick_clock()

    def _build_chat_panel(self):
        """Chatový panel — skrytý dokud uživatel neklikne na 💬."""
        self._chat_frame = ctk.CTkFrame(self.root, fg_color=BG2, corner_radius=0)
        # Nezobrazujeme — _toggle_chat ho přidá

        # Scrollovatelný seznam zpráv
        self._chat_scroll = ctk.CTkScrollableFrame(
            self._chat_frame,
            fg_color=BG2,
            corner_radius=0,
            height=200,
        )
        self._chat_scroll.pack(fill="both", expand=True, padx=0, pady=0)

        # Vstup pro chat
        inp_row = ctk.CTkFrame(self._chat_frame, fg_color=BG3, corner_radius=0, height=48)
        inp_row.pack(fill="x")
        inp_row.pack_propagate(False)

        self._chat_input = ctk.CTkEntry(
            inp_row,
            placeholder_text="Napiš zprávu...",
            font=("DM Sans", 13),
            fg_color=BG, text_color=FG,
            border_color=ORB_COLORS["idle"],
            border_width=1,
            corner_radius=6, height=32,
        )
        self._chat_input.place(x=10, rely=0.5, anchor="w", relwidth=0.80)
        self._chat_input.bind("<Return>", self._on_chat_enter)

        ctk.CTkButton(
            inp_row, text="↵",
            font=("Georgia", 16),
            fg_color=ORB_COLORS["idle"],
            hover_color="#7c3aed",
            text_color=BG,
            corner_radius=6, width=38, height=32,
            command=self._on_chat_enter,
        ).place(relx=0.96, rely=0.5, anchor="e")

    def _build_controls(self):
        """Dolní panel s mic tlačítkem, settings a theme togglem."""
        ctrl = ctk.CTkFrame(self.root, fg_color=BG2, corner_radius=0, height=110)
        ctrl.pack(fill="x", side="bottom")
        ctrl.pack_propagate(False)

        # Zlatý rámeček kolem mic tlačítka
        mic_ring = ctk.CTkFrame(
            ctrl,
            fg_color=BG2,
            border_color=ORB_COLORS["idle"],
            border_width=2,
            corner_radius=50,
            width=70, height=70,
        )
        mic_ring.place(relx=0.5, rely=0.42, anchor="center")
        mic_ring.pack_propagate(False)

        # Mic tlačítko — kulaté
        self.mic_btn = ctk.CTkButton(
            mic_ring,
            text="🎤",
            font=("DM Sans", 22),
            fg_color=ORB_COLORS["idle"],
            hover_color="#7c3aed",
            text_color=BG,
            corner_radius=50, width=62, height=62,
            command=self._on_mic,
        )
        self.mic_btn.place(relx=0.5, rely=0.5, anchor="center")

        # Stavový label pod mic tlačítkem
        self._mic_lbl = ctk.CTkLabel(
            ctrl,
            text="Klikni nebo stiskni mezerník",
            font=("DM Sans", 9),
            text_color=MUTED,
        )
        self._mic_lbl.place(relx=0.5, rely=0.86, anchor="center")

        # Vedlejší tlačítka — vlevo od středu
        side_left = ctk.CTkFrame(ctrl, fg_color=BG2, corner_radius=0)
        side_left.place(relx=0.18, rely=0.42, anchor="center")

        self._theme_btn = ctk.CTkButton(
            side_left, text="🌙",
            font=("DM Sans", 16), fg_color="#1e1b4b",
            hover_color="#2d2a6e", text_color=FG,
            corner_radius=8, width=38, height=38,
            command=self._toggle_theme,
        )
        self._theme_btn.pack()

        # Vedlejší tlačítka — vpravo od středu
        side_right = ctk.CTkFrame(ctrl, fg_color=BG2, corner_radius=0)
        side_right.place(relx=0.82, rely=0.42, anchor="center")

        ctk.CTkButton(
            side_right, text="💬",
            font=("DM Sans", 16), fg_color="#1e1b4b",
            hover_color="#2d2a6e", text_color=FG,
            corner_radius=8, width=38, height=38,
            command=self._toggle_chat,
        ).pack()

    # ── HODINY ───────────────────────────────────────

    def _tick_clock(self):
        self._clock_lbl.configure(text=datetime.now().strftime("%H:%M:%S"))
        self.root.after(1000, self._tick_clock)

    # ── VEŘEJNÉ API ──────────────────────────────────

    def set_state(self, state: str):
        """Nastaví stav orbu: idle | listening | thinking | speaking"""
        if state not in ORB_COLORS:
            return
        self._state = state
        self.orb.set_state(state)

        # Aktualizace stavového textu (s mezerami = letter-spacing)
        label = STATE_LABELS.get(state, state.upper())
        color = ORB_COLORS[state]
        self._status_lbl.configure(text=label, text_color=color)

        # Aktualizace mic labelu
        mic_labels = {
            "idle":      "Klikni nebo stiskni mezerník",
            "listening": "Poslouchám...",
            "thinking":  "Zpracovávám...",
            "speaking":  "Mluvím...",
        }
        self._mic_lbl.configure(text=mic_labels.get(state, ""))

        # Barva mic tlačítka odpovídá stavu
        self.mic_btn.configure(fg_color=color, hover_color=ORB_DARK.get(state, color))

    def add_message(self, text: str, sender: str):
        """Přidá zprávu do chatu. sender = 'user' | 'jarvis'"""
        bubble = ChatBubble(self._chat_scroll, text=text, sender=sender)
        bubble.pack(fill="x", padx=8, pady=4)
        # Scroll na konec
        self.root.after(50, lambda: self._chat_scroll._parent_canvas.yview_moveto(1.0))

        # Pokud je chat zavřený — otevři ho
        if not self._chat_open:
            self._toggle_chat()

    def set_status(self, text: str):
        """Nastaví doplňkový info text pod stavovým labelem."""
        self._info_lbl.configure(text=text)

    def run(self):
        """Spustí GUI mainloop."""
        self.root.mainloop()

    # ── INTERNÍ HANDLERS ─────────────────────────────

    def _on_mic(self):
        if self.on_mic_click:
            self.on_mic_click()

    def _on_space(self, event):
        # Mezerník = mikrofon (pokud focus není na textovém vstupu)
        focused = self.root.focus_get()
        if not isinstance(focused, (tk.Entry, ctk.CTkEntry)):
            self._on_mic()

    def _on_chat_enter(self, event=None):
        text = self._chat_input.get().strip()
        if not text:
            return
        self._chat_input.delete(0, "end")
        if self.on_send:
            self.on_send(text)
        else:
            # Demo: zobraz zprávu lokálně
            self.add_message(text, "user")

    def _toggle_chat(self):
        """Přepne zobrazení chat panelu."""
        if self._chat_open:
            self._chat_frame.pack_forget()
            self._chat_open = False
        else:
            self._chat_frame.pack(
                fill="x", side="bottom",
                before=self.root.pack_slaves()[-1],  # nad controls
            )
            self._chat_open = True

    def _toggle_theme(self):
        """Přepíná dark/light mód."""
        self._dark_mode = not self._dark_mode
        mode = "dark" if self._dark_mode else "light"
        ctk.set_appearance_mode(mode)
        self._theme_btn.configure(text="🌙" if self._dark_mode else "☀")


# ══════════════════════════════════════════════════════
#  DEMO — ukázka všech stavů
# ══════════════════════════════════════════════════════

def _demo(gui: JarvisGUI):
    """Cyklicky prochází všechny stavy pro ukázku."""
    states = ["idle", "listening", "thinking", "speaking"]
    messages = [
        ("Ahoj JARVIS, jak se máš?", "user"),
        ("Výborně! Jsem připraven ti pomoci.", "jarvis"),
        ("Otevři VS Code prosím.", "user"),
        ("Otevírám VS Code.", "jarvis"),
    ]
    idx = [0]
    msg_idx = [0]

    def cycle():
        state = states[idx[0] % len(states)]
        gui.set_state(state)
        gui.set_status(f"Demo stav: {state}")

        # Přidej zprávu každé 2 cykly
        if idx[0] % 2 == 0 and msg_idx[0] < len(messages):
            text, sender = messages[msg_idx[0]]
            gui.add_message(text, sender)
            msg_idx[0] += 1

        idx[0] += 1
        gui.root.after(2500, cycle)

    gui.root.after(1500, cycle)


if __name__ == "__main__":
    gui = JarvisGUI()

    # Nastav demo callbacky
    gui.on_mic_click = lambda: print("[MIC] Kliknuto!")
    gui.on_send      = lambda t: (print(f"[SEND] {t}"), gui.add_message(t, "user"))

    # Spusť demo animaci stavů
    _demo(gui)

    gui.run()
