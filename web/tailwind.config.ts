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
        bg:      "#040910",
        card:    "rgba(8,16,32,0.75)",
        cyan:    "#00c8ff",
        teal:    "#4ecdc4",
        green:   "#22d3a5",
        amber:   "#f59e0b",
        red:     "#f43f5e",
        purple:  "#a855f7",
        indigo:  "#6366f1",
        text:    "#dbeafe",
        muted:   "#4d7090",
        border:  "rgba(0,200,255,0.1)",
      },
      fontFamily: {
        hud:  ["Orbitron", "sans-serif"],
        mono: ["Share Tech Mono", "Courier New", "monospace"],
        ui:   ["Inter", "system-ui", "sans-serif"],
      },
      animation: {
        "logo-pulse":  "logoPulse 3s ease-in-out infinite",
        "orb-inner":   "orbInner 4s ease-in-out infinite",
        "orb-ring":    "orbRing 4s ease-in-out infinite",
        "orb-outer":   "orbOuter 4s ease-in-out infinite",
        "grid-drift":  "gridDrift 24s linear infinite",
        breathe:       "breathe 4s ease-in-out infinite",
        bounce:        "bounce 1.3s ease-in-out infinite",
        blink:         "blink 0.7s step-end infinite",
        pulse:         "pulse 1s ease-in-out infinite",
        spin:          "spin 0.8s linear infinite",
        "slide-up":    "slideUp 0.25s ease-out",
        "msg-in":      "msgIn 0.25s ease-out",
      },
      keyframes: {
        logoPulse: {
          "0%,100%": { boxShadow: "0 0 20px rgba(78,205,196,.4), 0 0 40px rgba(0,200,255,.15)" },
          "50%":     { boxShadow: "0 0 30px rgba(78,205,196,.6), 0 0 60px rgba(0,200,255,.25)" },
        },
        orbInner: {
          "0%,100%": { boxShadow: "0 0 18px rgba(78,205,196,.55), 0 0 36px rgba(78,205,196,.25)" },
          "50%":     { boxShadow: "0 0 28px rgba(78,205,196,.8),  0 0 56px rgba(78,205,196,.4)" },
        },
        orbRing: {
          "0%,100%": { transform: "scale(1)",   opacity: "0.45" },
          "50%":     { transform: "scale(1.12)", opacity: "0.18" },
        },
        orbOuter: {
          "0%,100%": { transform: "scale(1)",   opacity: "0.15" },
          "50%":     { transform: "scale(1.28)", opacity: "0" },
        },
        gridDrift: {
          "0%":   { backgroundPosition: "0 0" },
          "100%": { backgroundPosition: "48px 48px" },
        },
        breathe: {
          "0%,100%": { transform: "scale(1)" },
          "50%":     { transform: "scale(1.025)" },
        },
        bounce: {
          "0%,60%,100%": { transform: "translateY(0)",   opacity: "0.35" },
          "30%":          { transform: "translateY(-5px)", opacity: "1" },
        },
        blink: {
          "0%,100%": { opacity: "1" },
          "50%":     { opacity: "0" },
        },
        slideUp: {
          from: { opacity: "0", transform: "translateY(10px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        msgIn: {
          from: { opacity: "0", transform: "translateY(6px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
