"""
JARVIS GUI — Sci-fi HUD hlasový asistent
Tmavý modrý dark mode s neon cyan akcenty.
Animovaný orb s částicemi, HUD detaily, vysuvný chat panel.
"""

import math
import random
import tkinter as tk
import customtkinter as ctk
from datetime import datetime


# ══════════════════════════════════════════════════════
#  BAREVNÁ PALETA
# ══════════════════════════════════════════════════════

BG      = "#050a15"   # hlavní pozadí — tmavá námořní modrá
BG2     = "#0a1628"   # pozadí panelů
BG3     = "#0d1f3c"   # pozadí karet a tlačítek
FG      = "#e3f2fd"   # primární text
FG2     = "#90caf9"   # sekundární text
BORDER  = "#1a3a5c"   # okraje
CYAN    = "#00e5ff"   # neon cyan — hlavní akcent
BLUE    = "#1976d2"   # sekundární modrá

# Barvy orbu pro každý stav
ORB_COLORS = {
    "idle":      "#1565c0",
    "listening": "#00e5ff",
    "thinking":  "#7c4dff",
    "speaking":  "#00b0ff",
}

# Tmavší verze pro glow efekt
ORB_DARK = {
    "idle":      "#0d47a1",
    "listening": "#006064",
    "thinking":  "#4527a0",
    "speaking":  "#01579b",
}

# Popis stavů (s tečkou prefix)
STATE_LABELS = {
    "idle":      "● IDLE",
    "listening": "● LISTENING",
    "thinking":  "● THINKING",
    "speaking":  "● SPEAKING",
}


# ══════════════════════════════════════════════════════
#  POMOCNÉ FUNKCE
# ══════════════════════════════════════════════════════

def blend(color: str, bg: str, alpha: float) -> str:
    """Smíchá barvu s pozadím při dané průhlednosti (0.0–1.0)."""
    def p(h):
        h = h.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    cr, cg, cb = p(color)
    br, bg_, bb = p(bg)
    r = int(br + (cr - br) * max(0.0, min(1.0, alpha)))
    g = int(bg_ + (cg - bg_) * max(0.0, min(1.0, alpha)))
    b = int(bb + (cb - bb) * max(0.0, min(1.0, alpha)))
    return f"#{r:02x}{g:02x}{b:02x}"


def lerp_color(a: str, b: str, t: float) -> str:
    """Lineární interpolace mezi dvěma barvami (t = 0..1)."""
    return blend(b, a, t)


# ══════════════════════════════════════════════════════
#  ČÁSTICE
# ══════════════════════════════════════════════════════

class Particle:
    """
    Jedna částice pohybující se po eliptické dráze kolem středu orbu.
    Simuluje 3D pohyb projekcí do 2D roviny.
    """

    def __init__(self, cx: float, cy: float):
        self.cx        = cx
        self.cy        = cy
        self.orbit_r   = random.uniform(55, 125)    # poloměr dráhy (px)
        self.phase     = random.uniform(0, 2 * math.pi)
        self.base_speed = random.uniform(0.009, 0.033)
        # Naklopení elipsy — simuluje natočení ve 3D prostoru
        self.tilt      = random.uniform(0.18, 0.82)
        self.axis      = random.uniform(0, math.pi)  # rotace dráhy kolem osy Y
        # Vizuální vlastnosti
        self.size      = random.uniform(1.5, 3.5)
        # Fáze pro speaking pulsaci
        self.pulse_phase = random.uniform(0, 2 * math.pi)

    def get_xy(self, frame: int, speed_mult: float, orbit_mult: float) -> tuple:
        """
        Vrátí (x, y, z_depth) pro daný snímek.
        z_depth ∈ (-orbit_r, +orbit_r) — kladné = vpředu.
        """
        speed = self.base_speed * speed_mult
        angle = self.phase + speed * frame
        r     = self.orbit_r * orbit_mult

        # 3D eliptická dráha
        x3 = r * math.cos(angle)
        y3 = r * math.sin(angle) * self.tilt
        z3 = r * math.sin(angle) * (1.0 - self.tilt)

        # Projekce — rotace kolem osy Y o self.axis
        cos_a = math.cos(self.axis)
        sin_a = math.sin(self.axis)
        x2    = x3 * cos_a - z3 * sin_a
        y2    = y3
        depth = x3 * sin_a + z3 * cos_a   # hloubka = simulace Z

        return self.cx + x2, self.cy + y2, depth


# ══════════════════════════════════════════════════════
#  ORB CANVAS
# ══════════════════════════════════════════════════════

class OrbCanvas(tk.Canvas):
    """
    Animovaný ORB na tkinter Canvas.
    Kreslí se každých 30 ms přes root.after().

    Obsahuje:
      • 60 částic na eliptických drahách
      • 4 vrstvy vnitřního glow jádra
      • Vnější rotující ring se 4 tečkami
      • Přerušovaný druhý ring (rotuje opačně)
      • HUD rohy a boční level indikátory
      • Stavový text a hodiny
    """

    SIZE = 300   # rozměr canvasu (čtverec)

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            width=self.SIZE, height=self.SIZE,
            bg=BG, highlightthickness=0, bd=0,
            **kwargs,
        )
        self.cx = self.SIZE / 2
        self.cy = self.SIZE / 2

        # Stav a barevný přechod
        self._state        = "idle"
        self._color        = ORB_COLORS["idle"]
        self._target_color = self._color
        self._lerp_t       = 1.0

        # Animační čítač
        self._frame        = 0
        self._pulse        = 0.0       # sinusový puls glow jádra
        self._ring_angle   = 0.0       # úhel rotace hlavního ringu
        self._ring2_angle  = 0.0       # úhel druhého ringu (opačně)
        self._running      = True

        # 60 částic
        self._particles    = [Particle(self.cx, self.cy) for _ in range(60)]

        # Spusť animaci
        self._animate()

    # ── VEŘEJNÉ METODY ───────────────────────────────

    def set_state(self, state: str):
        """Nastaví stav orbu a zahájí barevný přechod."""
        if state not in ORB_COLORS:
            return
        self._state        = state
        self._target_color = ORB_COLORS[state]
        self._lerp_t       = 0.0

    def stop(self):
        """Zastaví animační smyčku."""
        self._running = False

    # ── ANIMACE ──────────────────────────────────────

    def _animate(self):
        if not self._running:
            return
        self._frame      += 1
        self._pulse      += 0.04
        self._ring_angle  = (self._ring_angle  + 1.1) % 360
        self._ring2_angle = (self._ring2_angle - 0.7) % 360

        # Plynulý přechod barvy
        if self._lerp_t < 1.0:
            self._lerp_t  = min(1.0, self._lerp_t + 0.05)
            self._color   = lerp_color(self._color, self._target_color, self._lerp_t)

        self._draw()
        self.after(30, self._animate)

    def _draw(self):
        self.delete("all")
        self._draw_hud_corners()
        self._draw_ring2()
        self._draw_ring()
        self._draw_glow()
        self._draw_particles()
        self._draw_hud_levels()
        self._draw_state_text()

    # ── VNITŘNÍ GLOW ─────────────────────────────────

    def _draw_glow(self):
        """Kreslí 4 soustředné kruhy (glow jádro), pulsující sinusem."""
        pulse = math.sin(self._pulse) * 8
        # (poloměr, průhlednost)
        layers = [(35, 0.40), (50, 0.25), (65, 0.15), (80, 0.08)]

        for base_r, alpha in layers:
            r = base_r + pulse * (base_r / 80)
            c = blend(self._color, BG, alpha)
            self.create_oval(
                self.cx - r, self.cy - r,
                self.cx + r, self.cy + r,
                fill=c, outline="",
            )

        # Jasné středové jádro
        r_core = 10 + math.sin(self._pulse) * 2
        c_core = blend(self._color, "#ffffff", 0.35)
        self.create_oval(
            self.cx - r_core, self.cy - r_core,
            self.cx + r_core, self.cy + r_core,
            fill=c_core, outline="",
        )

    # ── ČÁSTICE ──────────────────────────────────────

    def _draw_particles(self):
        """Kreslí 60 částic se stavově závislým chováním."""
        state = self._state

        # Parametry závisejí na stavu
        if state == "idle":
            speed_mult, orbit_mult = 1.0, 1.0
        elif state == "listening":
            speed_mult, orbit_mult = 1.7, 0.75   # stahují se ke středu
        elif state == "thinking":
            speed_mult, orbit_mult = 2.6, 1.0    # rychlé kroužení
        else:  # speaking
            speed_mult, orbit_mult = 1.4, 1.0

        for i, p in enumerate(self._particles):
            # Speaking: pulsace ven od středu
            om = orbit_mult
            if state == "speaking":
                om *= 1.0 + 0.22 * math.sin(self._frame * 0.09 + p.pulse_phase)

            x, y, depth = p.get_xy(self._frame, speed_mult, om)

            # Z-hloubka → jas a velikost
            z_norm = (depth / 130 + 1) / 2        # 0 = vzadu, 1 = vpředu
            size   = p.size * (0.35 + z_norm * 0.65)
            alpha  = 0.12 + z_norm * 0.75

            # Částice "za" orbem jsou tmavší
            if z_norm < 0.3:
                c = blend(ORB_DARK.get(state, self._color), BG, alpha * 0.55)
            else:
                c = blend(self._color, BG, alpha)

            if 0 < x < self.SIZE and 0 < y < self.SIZE:
                self.create_oval(
                    x - size, y - size, x + size, y + size,
                    fill=c, outline="",
                )

    # ── VNĚJŠÍ RING ───────────────────────────────────

    def _draw_ring(self):
        """Hlavní tenký ring (110px) s rotujícími 4 cyan tečkami."""
        r = 110
        c = blend(BORDER, BG, 0.7)
        self.create_oval(
            self.cx - r, self.cy - r,
            self.cx + r, self.cy + r,
            outline=c, width=1, fill="",
        )

        # 4 tečky rovnoměrně na ringu (rotují)
        dot_r = 4
        for i in range(4):
            angle = math.radians(self._ring_angle + i * 90)
            dx    = r * math.cos(angle)
            dy    = r * math.sin(angle)
            self.create_oval(
                self.cx + dx - dot_r, self.cy + dy - dot_r,
                self.cx + dx + dot_r, self.cy + dy + dot_r,
                fill=CYAN, outline="",
            )

    def _draw_ring2(self):
        """
        Druhý přerušovaný ring (125px), rotuje opačně.
        Přerušení simulovány obloukovými segmenty.
        """
        r     = 125
        c     = blend(BORDER, BG, 0.5)
        step  = 18      # stupňů na segment
        gap   = 8       # stupňů mezery

        for start in range(0, 360, step + gap):
            a1 = math.radians(start + self._ring2_angle)
            a2 = math.radians(start + step + self._ring2_angle)
            # Aproximuj oblouk čarami (8 úseků na segment)
            segs = 6
            pts = []
            for k in range(segs + 1):
                a = a1 + (a2 - a1) * k / segs
                pts.append(self.cx + r * math.cos(a))
                pts.append(self.cy + r * math.sin(a))
            if len(pts) >= 4:
                self.create_line(*pts, fill=c, width=1, smooth=True)

    # ── HUD ROHOVÉ ČÁRY ──────────────────────────────

    def _draw_hud_corners(self):
        """Malé L-shaped rohové čáry v každém rohu canvasu (12px, cyan)."""
        L = 14     # délka ramene
        w = 1
        c = blend(CYAN, BG, 0.7)
        corners = [
            # (x_start, y_start), směr x, směr y
            ((0,   0  ), ( 1,  0), ( 0,  1)),
            ((300, 0  ), (-1,  0), ( 0,  1)),
            ((0,   300), ( 1,  0), ( 0, -1)),
            ((300, 300), (-1,  0), ( 0, -1)),
        ]
        for (ox, oy), (hx, hy), (vx, vy) in corners:
            # vodorovné rameno
            self.create_line(ox, oy, ox + hx * L, oy + hy * L, fill=c, width=w)
            # svislé rameno
            self.create_line(ox, oy, ox + vx * L, oy + vy * L, fill=c, width=w)

    # ── HUD BOČNÍ LEVEL INDIKÁTORY ────────────────────

    def _draw_hud_levels(self):
        """3 malé vodorovné čárky vlevo a vpravo od orbu (level indikátory)."""
        c      = blend(CYAN, BG, 0.4)
        offsets = [-24, 0, 24]    # y-offset od středu

        # Levá strana
        for dy in offsets:
            y = self.cy + dy
            brightness = 0.4 + 0.3 * (1 - abs(dy) / 30)
            cc = blend(CYAN, BG, brightness)
            self.create_line(6, y, 20, y, fill=cc, width=1)

        # Pravá strana
        for dy in offsets:
            y = self.cy + dy
            brightness = 0.4 + 0.3 * (1 - abs(dy) / 30)
            cc = blend(CYAN, BG, brightness)
            self.create_line(280, y, 294, y, fill=cc, width=1)

    # ── STAVOVÝ TEXT ─────────────────────────────────

    def _draw_state_text(self):
        """Stavový label a hodiny pod orbem (uvnitř canvasu, spodní část)."""
        label = STATE_LABELS.get(self._state, self._state.upper())
        color = self._color

        # Stavový text (spodek canvasu)
        self.create_text(
            self.cx, self.SIZE - 26,
            text=label,
            font=("Courier New", 10),
            fill=color,
            anchor="center",
        )

        # Hodiny — aktuální čas
        ts = datetime.now().strftime("%H:%M:%S")
        self.create_text(
            self.cx, self.SIZE - 10,
            text=ts,
            font=("Courier New", 8),
            fill=BORDER,
            anchor="center",
        )


# ══════════════════════════════════════════════════════
#  CHAT BUBLINA
# ══════════════════════════════════════════════════════

class ChatBubble(ctk.CTkFrame):
    """
    Jedna chatová bublina ve vysuvném panelu.
    Uživatel: vpravo, zlatá; JARVIS: vlevo, modrá.
    """

    def __init__(self, parent, text: str, sender: str, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        is_user = (sender == "user")
        ts      = datetime.now().strftime("%H:%M")

        # Řádek s meta informacemi (emoji + timestamp)
        meta = ctk.CTkFrame(self, fg_color="transparent")
        meta.pack(fill="x", padx=4)

        if is_user:
            ctk.CTkLabel(meta, text="🧑", font=("DM Sans", 10)).pack(side="right")
            ctk.CTkLabel(meta, text=ts, font=("Courier New", 8),
                         text_color=BORDER).pack(side="right", padx=(0, 4))
        else:
            ctk.CTkLabel(meta, text="🤖", font=("DM Sans", 10)).pack(side="left")
            ctk.CTkLabel(meta, text=ts, font=("Courier New", 8),
                         text_color=BORDER).pack(side="left", padx=(4, 0))

        # Bublina
        bg_bubble  = BG3 if is_user else BG
        text_color = FG  if is_user else FG2
        anchor     = "e" if is_user else "w"
        pad_left   = (30, 6) if is_user else (6, 30)

        bubble = ctk.CTkFrame(
            self,
            fg_color=bg_bubble,
            border_color=CYAN if is_user else BORDER,
            border_width=1,
            corner_radius=8,
        )
        bubble.pack(anchor=anchor, padx=pad_left, pady=(2, 0))

        ctk.CTkLabel(
            bubble,
            text=text,
            font=("DM Sans", 11),
            text_color=text_color,
            wraplength=200,
            justify="right" if is_user else "left",
        ).pack(padx=8, pady=6)


# ══════════════════════════════════════════════════════
#  HLAVNÍ GUI
# ══════════════════════════════════════════════════════

class JarvisGUI:
    """
    Hlavní GUI třída JARVIS asistenta.

    Veřejné API:
      set_state(state: str)          — idle | listening | thinking | speaking
      add_message(text, sender)      — user | jarvis
      set_status(text)               — info text pod orbem
      run()                          — spustí mainloop

    Callbacky (nastav zvenčí):
      on_mic_click: callable
      on_send: callable (text: str)
    """

    CHAT_WIDTH = 280   # šířka chat panelu

    def __init__(self):
        # Callbacky pro integraci se zbytkem systému
        self.on_mic_click: callable = None
        self.on_send:         callable = None
        self.on_model_change: callable = None   # callback(model_name: str)

        self._state      = "idle"
        self._chat_open  = False
        self._chat_anim  = False       # probíhá animace?
        self._chat_cur_x = -self.CHAT_WIDTH   # aktuální x chat panelu

        self._setup_window()
        self._build_main()
        self._build_chat_panel()
        self._bind_keys()

    # ── OKNO ─────────────────────────────────────────

    def _setup_window(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.root = ctk.CTk()
        self.root.title("JARVIS")
        self.root.geometry("480x700")
        self.root.resizable(False, False)
        self.root.configure(fg_color=BG)

        # Vystředění okna na obrazovce
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x  = (sw - 480) // 2
        y  = (sh - 700) // 2
        self.root.geometry(f"480x700+{x}+{y}")

    # ── HLAVNÍ OBSAH ─────────────────────────────────

    def _build_main(self):
        """Sestaví hlavní layout: header → orb sekce → controls."""
        self._main = ctk.CTkFrame(self.root, fg_color=BG, corner_radius=0)
        self._main.place(x=0, y=0, width=480, height=700)

        self._build_header()
        self._build_orb_section()
        self._build_controls()

    def _build_header(self):
        """Tenký header s názvem JARVIS a stavem Ollama."""
        hdr = ctk.CTkFrame(self._main, fg_color=BG2, corner_radius=0, height=40)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr, text="J A R V I S",
            font=("Courier New", 13),
            text_color=CYAN,
        ).pack(side="left", padx=18)

        self._header_status = ctk.CTkLabel(
            hdr, text="● ONLINE",
            font=("Courier New", 9),
            text_color=BLUE,
        )
        self._header_status.pack(side="right", padx=16)

        # Dělicí linka
        ctk.CTkFrame(self._main, fg_color=BORDER, height=1, corner_radius=0).pack(fill="x")

    def _build_orb_section(self):
        """Sekce s animovaným orbem a stavovým textem."""
        orb_sec = ctk.CTkFrame(self._main, fg_color=BG, corner_radius=0)
        orb_sec.pack(fill="both", expand=True)

        # Wrapper pro centrování canvasu
        wrap = ctk.CTkFrame(orb_sec, fg_color=BG, corner_radius=0)
        wrap.pack(expand=True)

        # ORB canvas
        self.orb = OrbCanvas(wrap)
        self.orb.pack(pady=(16, 4))

        # Info text (set_status)
        self._info_lbl = ctk.CTkLabel(
            wrap, text="",
            font=("Courier New", 9),
            text_color=FG2,
        )
        self._info_lbl.pack()

    def _build_controls(self):
        """
        Spodní panel:
        [💬]  [🎤 kulaté]  [⚙️]
        """
        ctrl = ctk.CTkFrame(
            self._main, fg_color=BG2,
            border_color=BORDER, border_width=0,
            corner_radius=0, height=110,
        )
        ctrl.pack(fill="x", side="bottom")
        ctrl.pack_propagate(False)

        # Horní dělicí linka
        ctk.CTkFrame(ctrl, fg_color=BORDER, height=1, corner_radius=0).pack(fill="x")

        # Rámeček mic tlačítka (zlatý okraj)
        mic_ring = ctk.CTkFrame(
            ctrl,
            fg_color=BG2,
            border_color=CYAN,
            border_width=2,
            corner_radius=50,
            width=70, height=70,
        )
        mic_ring.place(relx=0.5, rely=0.44, anchor="center")
        mic_ring.pack_propagate(False)

        # Kulaté mic tlačítko
        self.mic_btn = ctk.CTkButton(
            mic_ring,
            text="🎤",
            font=("DM Sans", 22),
            fg_color=BG3,
            hover_color=BORDER,
            text_color=CYAN,
            corner_radius=50, width=62, height=62,
            border_color=CYAN, border_width=0,
            command=self._on_mic,
        )
        self.mic_btn.place(relx=0.5, rely=0.5, anchor="center")

        # Text pod tlačítkem
        self._mic_lbl = ctk.CTkLabel(
            ctrl,
            text="Klikni nebo stiskni mezerník",
            font=("Courier New", 9),
            text_color=FG2,
        )
        self._mic_lbl.place(relx=0.5, rely=0.88, anchor="center")

        # Chat toggle vlevo
        ctk.CTkButton(
            ctrl, text="💬",
            font=("DM Sans", 16), fg_color=BG3,
            hover_color=BORDER, text_color=FG2,
            corner_radius=8, width=38, height=38,
            command=self._toggle_chat,
        ).place(relx=0.16, rely=0.42, anchor="center")

        # Settings — otvírá model dialog vpravo
        ctk.CTkButton(
            ctrl, text="⚙",
            font=("DM Sans", 16), fg_color=BG3,
            hover_color=BORDER, text_color=FG2,
            corner_radius=8, width=38, height=38,
            command=self._open_model_dialog,
        ).place(relx=0.84, rely=0.42, anchor="center")

    # ── CHAT PANEL ───────────────────────────────────

    def _build_chat_panel(self):
        """
        Vysuvný chat panel (280px) ze leva.
        Ve výchozím stavu skrytý (x = -CHAT_WIDTH).
        Animovaně se vysouvá/zasunuje přes _slide_chat().
        """
        self._chat_panel = ctk.CTkFrame(
            self.root,
            fg_color=BG2,
            border_color=BORDER,
            border_width=0,
            corner_radius=0,
            width=self.CHAT_WIDTH,
        )
        # Umístění mimo obrazovku
        self._chat_panel.place(x=-self.CHAT_WIDTH, y=0,
                               width=self.CHAT_WIDTH, height=700)
        self._chat_panel.pack_propagate(False)

        # Nadpis panelu
        hdr = ctk.CTkFrame(self._chat_panel, fg_color=BG3, corner_radius=0, height=40)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr, text="KOMUNIKACE",
            font=("Courier New", 10),
            text_color=CYAN,
        ).pack(side="left", padx=12, pady=10)

        ctk.CTkButton(
            hdr, text="✕",
            font=("DM Sans", 12), fg_color=BG3,
            hover_color=BORDER, text_color=FG2,
            corner_radius=4, width=28, height=28,
            command=self._toggle_chat,
        ).pack(side="right", padx=6)

        ctk.CTkFrame(self._chat_panel, fg_color=BORDER, height=1, corner_radius=0).pack(fill="x")

        # Scrollovatelná oblast zpráv
        self._chat_scroll = ctk.CTkScrollableFrame(
            self._chat_panel,
            fg_color=BG2,
            corner_radius=0,
        )
        self._chat_scroll.pack(fill="both", expand=True)

        # Vstupní pole pro text
        inp_row = ctk.CTkFrame(self._chat_panel, fg_color=BG3,
                               corner_radius=0, height=48)
        inp_row.pack(fill="x", side="bottom")
        inp_row.pack_propagate(False)

        ctk.CTkFrame(inp_row, fg_color=BORDER, height=1, corner_radius=0).pack(fill="x")

        self._chat_input = ctk.CTkEntry(
            inp_row,
            placeholder_text="Napiš zprávu...",
            font=("DM Sans", 12),
            fg_color=BG, text_color=FG,
            border_color=BORDER, border_width=1,
            corner_radius=6, height=30,
        )
        self._chat_input.place(x=8, rely=0.5, anchor="w", relwidth=0.76)
        self._chat_input.bind("<Return>", self._on_chat_enter)

        ctk.CTkButton(
            inp_row, text="↵",
            font=("Georgia", 14),
            fg_color=BLUE, hover_color=BORDER,
            text_color=FG, corner_radius=6,
            width=32, height=30,
            command=self._on_chat_enter,
        ).place(relx=0.94, rely=0.5, anchor="center")

    # ── KLÁVESY ──────────────────────────────────────

    def _bind_keys(self):
        self.root.bind("<space>",  self._on_space)
        self.root.bind("<Escape>", self._on_escape)

    def _on_space(self, event):
        """Mezerník spustí mikrofon (pokud není focus na textovém vstupu)."""
        focused = self.root.focus_get()
        if not isinstance(focused, (tk.Entry, ctk.CTkEntry)):
            self._on_mic()

    def _on_escape(self, event):
        """Escape zavře chat panel."""
        if self._chat_open:
            self._toggle_chat()

    # ── VEŘEJNÉ API ──────────────────────────────────

    def set_state(self, state: str):
        """Nastaví stav orbu a aktualizuje UI prvky."""
        if state not in ORB_COLORS:
            return
        self._state = state
        self.orb.set_state(state)

        # Barva mic labelu odpovídá stavu
        labels = {
            "idle":      "Klikni nebo stiskni mezerník",
            "listening": "● Poslouchám...",
            "thinking":  "● Zpracovávám...",
            "speaking":  "● Mluvím...",
        }
        self._mic_lbl.configure(
            text=labels.get(state, ""),
            text_color=ORB_COLORS.get(state, FG2),
        )

        # Barva mic tlačítka
        self.mic_btn.configure(text_color=ORB_COLORS.get(state, CYAN))

    def add_message(self, text: str, sender: str):
        """Přidá zprávu do chat panelu. Pokud je panel zavřený, otevře ho."""
        bubble = ChatBubble(self._chat_scroll, text=text, sender=sender)
        bubble.pack(fill="x", padx=4, pady=4)
        # Scroll na konec
        self.root.after(60, lambda: self._chat_scroll._parent_canvas.yview_moveto(1.0))

        if not self._chat_open:
            self._toggle_chat()

    def set_status(self, text: str):
        """Nastaví info text pod orbem."""
        self._info_lbl.configure(text=text)

    def run(self):
        """Spustí GUI mainloop."""
        self.root.mainloop()

    # ── INTERNÍ HANDLERS ─────────────────────────────

    def _on_mic(self):
        if self.on_mic_click:
            self.on_mic_click()

    def _open_model_dialog(self):
        """Dialog pro výběr Ollama modelu — stáhne seznam z Ollama."""
        import threading, requests as _req

        win = ctk.CTkToplevel(self.root)
        win.title("Výběr modelu")
        win.geometry("340x220")
        win.configure(fg_color=BG2)
        win.grab_set()
        win.lift()

        ctk.CTkLabel(win, text="VÝBĚR MODELU", font=("Courier New", 11),
                     text_color=CYAN).pack(pady=(16, 8))

        var = ctk.StringVar(value="Načítám...")
        opt = ctk.CTkOptionMenu(
            win, variable=var, values=["Načítám..."],
            fg_color=BG3, button_color=BLUE, button_hover_color=BORDER,
            text_color=FG, dropdown_text_color=FG, width=280,
        )
        opt.pack(pady=6)

        status_lbl = ctk.CTkLabel(win, text="", font=("Courier New", 9),
                                   text_color=FG2)
        status_lbl.pack(pady=4)

        def _load():
            try:
                r = _req.get("http://localhost:11434/api/tags", timeout=4)
                models = [m["name"] for m in r.json().get("models", [])]
                if not models:
                    models = ["Žádné modely"]
                win.after(0, lambda: opt.configure(values=models))
                win.after(0, lambda: var.set(models[0]))
                win.after(0, lambda: status_lbl.configure(
                    text=f"{len(models)} modelů dostupných"))
            except Exception as e:
                win.after(0, lambda: status_lbl.configure(
                    text=f"Chyba: {e}", text_color="#ef5350"))

        threading.Thread(target=_load, daemon=True).start()

        def _apply():
            model = var.get()
            if model and model != "Načítám..." and model != "Žádné modely":
                if self.on_model_change:
                    self.on_model_change(model)
                status_lbl.configure(text=f"✓ Model: {model}", text_color=CYAN)
            win.after(800, win.destroy)

        ctk.CTkButton(
            win, text="Použít",
            fg_color=BLUE, hover_color=BORDER, text_color=FG,
            corner_radius=6, width=140, height=34,
            command=_apply,
        ).pack(pady=12)

    def _on_chat_enter(self, event=None):
        text = self._chat_input.get().strip()
        if not text:
            return
        self._chat_input.delete(0, "end")
        if self.on_send:
            self.on_send(text)
        else:
            self.add_message(text, "user")

    # ── CHAT SLIDE ANIMACE ────────────────────────────

    def _toggle_chat(self):
        """Přepíná chat panel — spouští animaci vysunutí/zasunutí."""
        if self._chat_anim:
            return
        self._chat_open  = not self._chat_open
        self._chat_anim  = True
        target = 0 if self._chat_open else -self.CHAT_WIDTH
        self._slide_chat(target)

    def _slide_chat(self, target: int):
        """Rekurzivně animuje x-pozici chat panelu (30px/krok, 12ms)."""
        cur  = self._chat_cur_x
        step = 30 if target > cur else -30

        if abs(target - cur) <= abs(step):
            self._chat_cur_x = target
            self._chat_panel.place(x=target, y=0,
                                   width=self.CHAT_WIDTH, height=700)
            self._chat_anim = False
            return

        self._chat_cur_x += step
        self._chat_panel.place(x=self._chat_cur_x, y=0,
                               width=self.CHAT_WIDTH, height=700)
        self.root.after(12, lambda: self._slide_chat(target))


# ══════════════════════════════════════════════════════
#  DEMO — ukázka animace všech stavů
# ══════════════════════════════════════════════════════

def _run_demo(gui: JarvisGUI):
    """
    Demo sekvence:
    0s  → idle
    2s  → listening + zpráva uživatele
    4s  → thinking
    6s  → speaking + zpráva JARVIS
    8s  → idle (cyklus se opakuje)
    """
    sequence = [
        (0,    "idle",      None,       None),
        (2000, "listening", "user",     "Jaký je čas?"),
        (4000, "thinking",  None,       None),
        (6000, "speaking",  "jarvis",   "Je 14:37. Mohu pomoci s něčím dalším?"),
        (8000, "idle",      None,       None),
        (9500, "listening", "user",     "Otevři VS Code prosím."),
        (11500,"thinking",  None,       None),
        (13000,"speaking",  "jarvis",   "Otevírám VS Code."),
        (15000,"idle",      None,       None),
    ]

    def step(i=0):
        if i >= len(sequence):
            # Opakuj od začátku
            gui.root.after(1000, lambda: step(0))
            return
        delay, state, sender, text = sequence[i]
        gui.root.after(delay, lambda: _apply(state, sender, text))
        gui.root.after(delay, lambda: step(i + 1) if i + 1 < len(sequence) else None)

    def _apply(state, sender, text):
        gui.set_state(state)
        if sender and text:
            gui.add_message(text, sender)
        labels = {
            "idle":      "",
            "listening": "Analyzuji audio vstup...",
            "thinking":  "Zpracovávám dotaz...",
            "speaking":  "Generuji odpověď...",
        }
        gui.set_status(labels.get(state, ""))

    gui.root.after(500, lambda: step(0))


if __name__ == "__main__":
    gui = JarvisGUI()

    # Demo callbacky
    gui.on_mic_click = lambda: (
        gui.set_state("listening"),
        gui.set_status("Poslouchám..."),
    )
    gui.on_send = lambda t: gui.add_message(t, "user")

    # Spusť demo sekvenci
    _run_demo(gui)

    gui.run()
