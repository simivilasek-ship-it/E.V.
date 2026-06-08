import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./store/**/*.{ts,tsx}",
  ],
  darkMode: ["class", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        // Match globals.css exactly
        bg:      "#0a0b10",
        card:    "rgba(18,20,28,0.82)",
        accent:  "#6366f1",
        cyan:    "#38bdf8",
        teal:    "#2dd4bf",
        green:   "#34d399",
        amber:   "#fbbf24",
        red:     "#f87171",
        purple:  "#a78bfa",
        blue:    "#60a5fa",
        text:    "#f1f5f9",
        muted:   "#64748b",
        border:  "rgba(148,163,184,0.12)",
      },
      fontFamily: {
        // Fonts actually loaded in layout.tsx
        display: ["DM Sans", "system-ui", "sans-serif"],
        mono:    ["IBM Plex Mono", "JetBrains Mono", "monospace"],
        ui:      ["DM Sans", "system-ui", "sans-serif"],
        // Keep hud as alias for mono (Orbitron not loaded)
        hud:     ["IBM Plex Mono", "monospace"],
      },
      borderRadius: {
        DEFAULT: "12px",
        lg:      "16px",
        sm:      "8px",
        pill:    "999px",
      },
      animation: {
        "orb-glow":   "orbGlow 2.5s ease-in-out infinite",
        "slide-up":   "slideUp 0.22s ease forwards",
        "msg-in":     "msgIn 0.18s ease forwards",
        "shimmer":    "shimmer 1.4s infinite",
        "pulse-dot":  "pulseDot 1s infinite",
        "fade-in":    "fadeIn 0.3s ease forwards",
      },
    },
  },
  plugins: [],
};

export default config;
