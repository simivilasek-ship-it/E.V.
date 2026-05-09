"""
JARVIS v3.0 — Desktop GUI
Rozdělený layout: levý panel (orb + ovládání) + pravý panel (chat).
Sci-fi HUD design, tmavá modrá paleta.
"""

import math
import random
import tkinter as tk
import customtkinter as ctk
from datetime import datetime


# ══════════════════════════════════════════════════════
#  BARVY
# ══════════════════════════════════════════════════════

BG      = "#070b12"   # hlavní pozadí
BG2     = "#0b1220"   # panely
BG3     = "#0f1a2e"   # karty / vstupy
FG      = "#e2f0ff"   # primární text
FG2     = "#7ea8d4"   # sekundární text
BORDER  = "#1a3050"   # okraje
CYAN    = "#00d4ff"   # hlavní akcent
CYAN2   = "#0099bb"   # tmavší cyan
GREEN   = "#00e676"
RED     = "#ff5252"
PURPLE  = "#7c4dff"
LBLUE   = "#40c4ff"

ORB_COLORS = {
    "idle":      "#1565c0",
    "listening": "#00d4ff",
    "thinking":  "#7c4dff",
    "speaking":  "#00e676",
}
ORB_DARK = {
    "idle":      "#0d3a7a",
    "listening": "#005577",
    "thinking":  "#3d1a80",
    "speaking":  "#006633",
}
STATE_LABELS = {
    "idle":      "● IDLE",
    "listening": "● LISTENING",
    "thinking":  "● THINKING",
    "speaking":  "● SPEAKING",
}


# ══════════════════════════════════════════════════════
#  BARVA BLEND
# ══════════════════════════════════════════════════════

def blend(color: str, bg: str, alpha: float) -> str:
    def p(h):
        h = h.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    cr, cg, cb = p(color)
    br, bg_, bb = p(bg)
    a = max(0.0, min(1.0, alpha))
    return f"#{int(br+(cr-br)*a):02x}{int(bg_+(cg-bg_)*a):02x}{int(bb+(cb-bb)*a):02x}"


def lerp(a: str, b: str, t: float) -> str:
    return blend(b, a, t)


# ══════════════════════════════════════════════════════
#  ČÁSTICE
# ══════════════════════════════════════════════════════

class Particle:
    def __init__(self, cx, cy):
        self.cx = cx; self.cy = cy
        self.orbit_r   = random.uniform(50, 110)
        self.phase     = random.uniform(0, 2*math.pi)
        self.base_speed = random.uniform(0.008, 0.030)
        self.tilt      = random.uniform(0.2, 0.8)
        self.axis      = random.uniform(0, math.pi)
        self.size      = random.uniform(1.5, 3.2)
        self.pulse_p   = random.uniform(0, 2*math.pi)

    def pos(self, frame, speed_mult, orbit_mult):
        sp = self.base_speed * speed_mult
        a  = self.phase + sp * frame
        R  = self.orbit_r * orbit_mult
        x3 = R * math.cos(a)
        y3 = R * math.sin(a) * self.tilt
        z3 = R * math.sin(a) * (1 - self.tilt)
        ca, sa = math.cos(self.axis), math.sin(self.axis)
        return self.cx + x3*ca - z3*sa, self.cy + y3, x3*sa + z3*ca


# ══════════════════════════════════════════════════════
#  ORB CANVAS
# ══════════════════════════════════════════════════════

class OrbCanvas(tk.Canvas):
    """Animovaný orb — 240×240 px, 30ms refresh."""

    SIZE = 240

    def __init__(self, parent, **kw):
        super().__init__(parent, width=self.SIZE, height=self.SIZE,
                         bg=BG, highlightthickness=0, bd=0, **kw)
        self.cx = self.cy = self.SIZE / 2
        self._state      = "idle"
        self._color      = ORB_COLORS["idle"]
        self._tgt        = self._color
        self._lerp_t     = 1.0
        self._frame      = 0
        self._pulse      = 0.0
        self._ring_a     = 0.0
        self._ring2_a    = 0.0
        self._running    = True
        self._particles  = [Particle(self.cx, self.cy) for _ in range(55)]
        self._animate()

    def set_state(self, s):
        if s in ORB_COLORS:
            self._state = s
            self._tgt   = ORB_COLORS[s]
            self._lerp_t = 0.0

    def stop(self):
        self._running = False

    def _animate(self):
        if not self._running: return
        self._frame  += 1
        self._pulse  += 0.04
        self._ring_a  = (self._ring_a  + 1.1) % 360
        self._ring2_a = (self._ring2_a - 0.7) % 360
        if self._lerp_t < 1.0:
            self._lerp_t = min(1.0, self._lerp_t + 0.06)
            self._color  = lerp(self._color, self._tgt, self._lerp_t)
        self._draw()
        self.after(30, self._animate)

    def _draw(self):
        self.delete("all")
        self._draw_hud()
        self._draw_ring2()
        self._draw_ring()
        self._draw_glow()
        self._draw_particles()

    def _draw_glow(self):
        pulse = math.sin(self._pulse) * 6
        for base_r, alpha in [(28,0.45),(42,0.28),(56,0.16),(70,0.08)]:
            r = base_r + pulse * (base_r / 70)
            c = blend(self._color, BG, alpha)
            self.create_oval(self.cx-r, self.cy-r, self.cx+r, self.cy+r, fill=c, outline="")
        rc = 9 + math.sin(self._pulse)*2
        self.create_oval(self.cx-rc, self.cy-rc, self.cx+rc, self.cy+rc,
                         fill=blend(self._color, "#ffffff", 0.4), outline="")

    def _draw_particles(self):
        state = self._state
        mults = {"idle":(1.0,1.0),"listening":(1.7,0.72),"thinking":(2.5,1.0),"speaking":(1.4,1.0)}
        sm, om = mults.get(state,(1.0,1.0))
        for i, p in enumerate(self._particles):
            om2 = om
            if state == "speaking":
                om2 *= 1.0 + 0.22*math.sin(self._frame*0.09 + p.pulse_p)
            x, y, depth = p.pos(self._frame, sm, om2)
            zn    = (depth/(110*om2) + 1)/2
            size  = p.size * (0.35 + zn*0.65)
            alpha = 0.1 + zn*0.78
            c = blend(ORB_DARK.get(state,self._color), BG, alpha*0.5) if zn < 0.3 \
                else blend(self._color, BG, alpha)
            if 0 < x < self.SIZE and 0 < y < self.SIZE:
                self.create_oval(x-size, y-size, x+size, y+size, fill=c, outline="")

    def _draw_ring(self):
        r = 92
        self.create_oval(self.cx-r, self.cy-r, self.cx+r, self.cy+r,
                         outline=blend(BORDER, BG, 0.8), width=1, fill="")
        for i in range(4):
            a = math.radians(self._ring_a + i*90)
            dx, dy = r*math.cos(a), r*math.sin(a)
            self.create_oval(self.cx+dx-3.5, self.cy+dy-3.5,
                             self.cx+dx+3.5, self.cy+dy+3.5,
                             fill=blend(CYAN, BG, 0.9), outline="")

    def _draw_ring2(self):
        r = 106
        for start in range(0, 360, 22):
            a1 = math.radians(start + self._ring2_a)
            a2 = math.radians(start + 14 + self._ring2_a)
            pts = []
            for k in range(7):
                a = a1 + (a2-a1)*k/6
                pts += [self.cx+r*math.cos(a), self.cy+r*math.sin(a)]
            if len(pts) >= 4:
                self.create_line(*pts, fill=blend(BORDER,BG,0.55), width=1, smooth=True)

    def _draw_hud(self):
        L, c = 12, blend(CYAN, BG, 0.5)
        S = self.SIZE
        corners = [((0,0),(1,0),(0,1)),((S,0),(-1,0),(0,1)),
                   ((0,S),(1,0),(0,-1)),((S,S),(-1,0),(0,-1))]
        for (ox,oy),(hx,hy),(vx,vy) in corners:
            self.create_line(ox, oy, ox+hx*L, oy+hy*L, fill=c, width=1)
            self.create_line(ox, oy, ox+vx*L, oy+vy*L, fill=c, width=1)


# ══════════════════════════════════════════════════════
#  HLAVNÍ GUI
# ══════════════════════════════════════════════════════

class JarvisGUI:
    """
    Rozdělený layout 820×560:
    ┌─────────────────┬──────────────────────────┐
    │  ORB + STAV     │  CHAT LOG                │
    │  ovládání       │  zprávy                  │
    │                 │  input                   │
    └─────────────────┴──────────────────────────┘

    Veřejné API:
      set_state(state)          — idle|listening|thinking|speaking
      add_message(text, sender) — user|jarvis
      set_status(text)          — info pod orbem
      on_mic_click, on_send, on_model_change — callbacky
    """

    W, H = 820, 560
    LEFT_W = 300

    def __init__(self):
        self.on_mic_click:    callable = None
        self.on_send:         callable = None
        self.on_model_change: callable = None

        self._state = "idle"
        self._setup()
        self._build()

    # ── OKNO ─────────────────────────────────────────

    def _setup(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.root = ctk.CTk()
        self.root.title("JARVIS")
        self.root.geometry(f"{self.W}x{self.H}")
        self.root.resizable(False, False)
        self.root.configure(fg_color=BG)
        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{self.W}x{self.H}+{(sw-self.W)//2}+{(sh-self.H)//2}")
        self.root.bind("<Return>", self._on_enter)
        self.root.bind("<space>", self._on_space)

    # ── LAYOUT ───────────────────────────────────────

    def _build(self):
        # Hlavní dělení: levý panel | pravý panel
        left  = ctk.CTkFrame(self.root, fg_color=BG2,
                              width=self.LEFT_W, height=self.H, corner_radius=0)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        right = ctk.CTkFrame(self.root, fg_color=BG, corner_radius=0)
        right.pack(side="left", fill="both", expand=True)

        # Svislý oddělovač
        ctk.CTkFrame(self.root, fg_color=BORDER, width=1,
                     corner_radius=0, height=self.H).place(x=self.LEFT_W, y=0)

        self._build_left(left)
        self._build_right(right)

    # ── LEVÝ PANEL ────────────────────────────────────

    def _build_left(self, parent):
        # Název aplikace
        hdr = ctk.CTkFrame(parent, fg_color=BG, corner_radius=0, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="J A R V I S",
                     font=("Courier New", 15), text_color=CYAN).pack(
            side="left", padx=16, pady=12)

        self._status_dot = ctk.CTkLabel(hdr, text="●", font=("DM Sans", 10),
                                         text_color=BORDER)
        self._status_dot.pack(side="right", padx=14)

        ctk.CTkFrame(parent, fg_color=BORDER, height=1, corner_radius=0).pack(fill="x")

        # Orb — vystředěný
        orb_frame = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=0)
        orb_frame.pack(fill="x", pady=(18, 0))

        self.orb = OrbCanvas(orb_frame)
        self.orb.pack(anchor="center")

        # Stav pod orbem
        self._state_lbl = ctk.CTkLabel(
            orb_frame, text="● IDLE",
            font=("Courier New", 10), text_color=ORB_COLORS["idle"])
        self._state_lbl.pack(pady=(6, 2))

        # Status info
        self._info_lbl = ctk.CTkLabel(
            orb_frame, text="",
            font=("DM Sans", 10), text_color=FG2)
        self._info_lbl.pack(pady=(0, 8))

        # Hodiny
        self._clock = ctk.CTkLabel(
            orb_frame, text="",
            font=("Courier New", 9), text_color=BORDER)
        self._clock.pack()
        self._tick_clock()

        ctk.CTkFrame(parent, fg_color=BORDER, height=1, corner_radius=0).pack(fill="x", pady=(12, 0))

        # Model selector
        self._build_model_bar(parent)

        ctk.CTkFrame(parent, fg_color=BORDER, height=1, corner_radius=0).pack(fill="x", pady=(0, 0))

        # Mic tlačítko
        self._build_mic_area(parent)

    def _build_model_bar(self, parent):
        bar = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=0, height=40)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(bar, text="MODEL", font=("Courier New", 8),
                     text_color=BORDER).pack(side="left", padx=10)

        self._model_var = ctk.StringVar(value="qwen2.5:3b")
        self._model_opt = ctk.CTkOptionMenu(
            bar,
            variable=self._model_var,
            values=["qwen2.5:3b", "llama3.1:8b", "llama3.2:3b",
                    "mistral:7b", "deepseek-coder:latest"],
            command=self._on_model_select,
            fg_color=BG3, button_color=CYAN2,
            button_hover_color=BORDER,
            text_color=FG, dropdown_text_color=FG,
            font=("DM Sans", 11),
            width=170, height=28,
            corner_radius=4,
        )
        self._model_opt.pack(side="left", padx=6)

    def _build_mic_area(self, parent):
        area = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=0)
        area.pack(fill="both", expand=True)

        # Velké mic tlačítko — centrované
        mic_wrap = ctk.CTkFrame(area, fg_color=BG2, corner_radius=0)
        mic_wrap.place(relx=0.5, rely=0.38, anchor="center")

        ring = ctk.CTkFrame(mic_wrap, fg_color=BG2,
                            border_color=CYAN, border_width=2,
                            corner_radius=50, width=72, height=72)
        ring.pack()
        ring.pack_propagate(False)

        self.mic_btn = ctk.CTkButton(
            ring, text="🎤",
            font=("DM Sans", 24),
            fg_color=BG3, hover_color=BORDER,
            text_color=CYAN,
            corner_radius=50, width=64, height=64,
            command=self._on_mic)
        self.mic_btn.place(relx=0.5, rely=0.5, anchor="center")

        self._mic_lbl = ctk.CTkLabel(
            mic_wrap, text="Klikni nebo mezerník",
            font=("Courier New", 9), text_color=FG2)
        self._mic_lbl.pack(pady=(6, 0))

        # Tlačítka pod mic
        btn_row = ctk.CTkFrame(area, fg_color=BG2, corner_radius=0)
        btn_row.place(relx=0.5, rely=0.72, anchor="center")

        for txt, cmd in [("🗑", self._clear_chat), ("🧠", self._clear_mem)]:
            ctk.CTkButton(btn_row, text=txt,
                          font=("DM Sans", 14), fg_color=BG3,
                          hover_color=BORDER, text_color=FG2,
                          corner_radius=8, width=36, height=36,
                          command=cmd).pack(side="left", padx=4)

    # ── PRAVÝ PANEL (CHAT) ────────────────────────────

    def _build_right(self, parent):
        # Chat nadpis
        hdr = ctk.CTkFrame(parent, fg_color=BG, corner_radius=0, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="KOMUNIKACE",
                     font=("Courier New", 10), text_color=BORDER).pack(
            side="left", padx=16, pady=14)

        ctk.CTkFrame(parent, fg_color=BORDER, height=1, corner_radius=0).pack(fill="x")

        # Chat log
        self._chat = ctk.CTkScrollableFrame(
            parent, fg_color=BG, corner_radius=0)
        self._chat.pack(fill="both", expand=True, padx=0, pady=0)

        ctk.CTkFrame(parent, fg_color=BORDER, height=1, corner_radius=0).pack(fill="x")

        # Input řádek
        inp = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=0, height=56)
        inp.pack(fill="x")
        inp.pack_propagate(False)

        self._input = ctk.CTkEntry(
            inp,
            placeholder_text="Napiš příkaz pro JARVIS...",
            font=("DM Sans", 13),
            fg_color=BG3, text_color=FG,
            border_color=BORDER, border_width=1,
            corner_radius=8, height=36,
        )
        self._input.place(x=12, rely=0.5, anchor="w", relwidth=0.84)
        self._input.bind("<Return>", self._on_enter)
        self._input.focus()

        ctk.CTkButton(
            inp, text="↵",
            font=("Georgia", 18),
            fg_color=CYAN2, hover_color=BORDER,
            text_color=FG, corner_radius=8,
            width=42, height=36,
            command=self._send,
        ).place(relx=0.97, rely=0.5, anchor="e")

        # Uvítání
        self._add_sys("JARVIS v3.0 připraven.")

    # ── CHAT HELPERS ─────────────────────────────────

    def _add_sys(self, text):
        f = ctk.CTkFrame(self._chat, fg_color="transparent", corner_radius=0)
        f.pack(fill="x", pady=2)
        ctk.CTkLabel(f, text=text, font=("Courier New", 9),
                     text_color=BORDER).pack(anchor="center")

    def add_message(self, text: str, sender: str):
        is_user = (sender == "user")
        ts = datetime.now().strftime("%H:%M")

        row = ctk.CTkFrame(self._chat, fg_color="transparent", corner_radius=0)
        row.pack(fill="x", padx=10, pady=4)

        # Meta
        meta = ctk.CTkFrame(row, fg_color="transparent")
        meta.pack(fill="x")
        if is_user:
            ctk.CTkLabel(meta, text=f"🧑  {ts}",
                         font=("Courier New", 8), text_color=BORDER).pack(side="right")
        else:
            ctk.CTkLabel(meta, text=f"🤖  {ts}",
                         font=("Courier New", 8), text_color=BORDER).pack(side="left")

        # Bublina
        bubble = ctk.CTkFrame(
            row,
            fg_color=BG3 if is_user else "#080f1e",
            border_color=CYAN2 if is_user else BORDER,
            border_width=1,
            corner_radius=10,
        )
        bubble.pack(
            anchor="e" if is_user else "w",
            padx=(60, 0) if is_user else (0, 60),
            pady=(2, 0),
        )

        ctk.CTkLabel(
            bubble, text=text,
            font=("DM Sans", 12),
            text_color=FG if is_user else FG2,
            wraplength=300,
            justify="right" if is_user else "left",
            anchor="e" if is_user else "w",
        ).pack(padx=12, pady=7)

        # Scroll dolů
        self.root.after(60, lambda: self._chat._parent_canvas.yview_moveto(1.0))

    # ── HODINY ───────────────────────────────────────

    def _tick_clock(self):
        self._clock.configure(text=datetime.now().strftime("%H:%M:%S"))
        self.root.after(1000, self._tick_clock)

    # ── VEŘEJNÉ API ──────────────────────────────────

    def set_state(self, state: str):
        if state not in ORB_COLORS:
            return
        self._state = state
        self.orb.set_state(state)
        self._state_lbl.configure(
            text=STATE_LABELS.get(state, state.upper()),
            text_color=ORB_COLORS[state])
        mic_texts = {
            "idle":      "Klikni nebo mezerník",
            "listening": "● Poslouchám...",
            "thinking":  "● Zpracovávám...",
            "speaking":  "● Mluvím...",
        }
        self._mic_lbl.configure(
            text=mic_texts.get(state, ""),
            text_color=ORB_COLORS.get(state, FG2))
        self.mic_btn.configure(text_color=ORB_COLORS.get(state, CYAN))
        dot_colors = {"idle": BORDER, "listening": RED,
                      "thinking": PURPLE, "speaking": GREEN}
        self._status_dot.configure(
            text_color=dot_colors.get(state, BORDER))

    def set_status(self, text: str):
        self._info_lbl.configure(text=text)

    def run(self):
        self.root.mainloop()

    # ── INTERNÍ ──────────────────────────────────────

    def _on_mic(self):
        if self.on_mic_click:
            self.on_mic_click()

    def _on_space(self, event):
        if not isinstance(self.root.focus_get(), (tk.Entry, ctk.CTkEntry)):
            self._on_mic()

    def _on_enter(self, event=None):
        self._send()

    def _send(self):
        text = self._input.get().strip()
        if not text:
            return
        self._input.delete(0, "end")
        if self.on_send:
            self.on_send(text)
        else:
            self.add_message(text, "user")

    def _clear_chat(self):
        for w in self._chat.winfo_children():
            w.destroy()
        self._add_sys("Log vymazán.")

    def _clear_mem(self):
        self._add_sys("Paměť vymazána.")
        # Volající kód (JarvisApp) napojí llm.clear_history()

    def _on_model_select(self, value):
        if self.on_model_change:
            self.on_model_change(value)
        self._add_sys(f"Model: {value}")

    def update_model_list(self, models: list, current: str = ""):
        """Aktualizuje dropdown s dostupnými modely z Ollama."""
        if models:
            self._model_opt.configure(values=models)
        if current:
            self._model_var.set(current)


# ══════════════════════════════════════════════════════
#  DEMO
# ══════════════════════════════════════════════════════

def _demo(gui: JarvisGUI):
    seq = [
        (0,    "idle",      None,    None),
        (1500, "listening", "user",  "Zahraj Let Me Love You Justin Bieber"),
        (3500, "thinking",  None,    None),
        (5000, "speaking",  "jarvis","Přehrávám: Let Me Love You od Justin Biebera."),
        (7000, "idle",      None,    None),
        (8500, "listening", "user",  "Kolik je hodin?"),
        (10000,"thinking",  None,    None),
        (11000,"speaking",  "jarvis","Je 18:42."),
        (12500,"idle",      None,    None),
    ]
    def step(i=0):
        if i >= len(seq):
            gui.root.after(2000, lambda: step(0))
            return
        delay, state, sender, text = seq[i]
        def apply():
            gui.set_state(state)
            if sender and text:
                gui.add_message(text, sender)
        gui.root.after(delay, apply)
        if i + 1 < len(seq):
            gui.root.after(seq[i+1][0], lambda ii=i+1: step(ii))
    step()


if __name__ == "__main__":
    gui = JarvisGUI()
    gui.on_send = lambda t: gui.add_message(t, "user")
    _demo(gui)
    gui.run()
