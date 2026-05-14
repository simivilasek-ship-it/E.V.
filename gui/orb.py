"""
Animovaný orb — Particle + OrbCanvas.
"""

import math
import random
import tkinter as tk

from gui.constants import BG, BORDER, CYAN, ORB_COLORS, ORB_DARK, blend, lerp


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

    _speed_mult = 1.0

    def set_speed(self, multiplier: float):
        """Nastaví rychlost animace (0.1 = pomalé, 1.0 = normální)"""
        self._speed_mult = max(0.1, min(1.0, multiplier))

    def set_state(self, s):
        if s in ORB_COLORS:
            self._state = s
            self._tgt   = ORB_COLORS[s]
            self._lerp_t = 0.0

    def stop(self):
        self._running = False

    def _animate(self):
        if not self._running: return
        sm = self._speed_mult
        self._frame  += 1 * sm
        self._pulse  += 0.04 * sm
        self._ring_a  = (self._ring_a  + 1.1 * sm) % 360
        self._ring2_a = (self._ring2_a - 0.7 * sm) % 360
        if self._lerp_t < 1.0:
            self._lerp_t = min(1.0, self._lerp_t + 0.06 * sm)
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


class MiniOrbCanvas(OrbCanvas):
    """Malý orb pro top bar — 48×48 px, méně částic."""

    SIZE = 48

    def __init__(self, parent, **kw):
        # Přeskočí OrbCanvas.__init__ a zavolá Canvas přímo
        tk.Canvas.__init__(self, parent, width=self.SIZE, height=self.SIZE,
                           bg=BG, highlightthickness=0, bd=0, **kw)
        self.cx = self.cy = self.SIZE / 2
        self._state     = "idle"
        self._color     = ORB_COLORS["idle"]
        self._tgt       = self._color
        self._lerp_t    = 1.0
        self._frame     = 0
        self._pulse     = 0.0
        self._ring_a    = 0.0
        self._ring2_a   = 0.0
        self._running   = True
        self._particles = [Particle(self.cx, self.cy) for _ in range(12)]
        self._animate()
