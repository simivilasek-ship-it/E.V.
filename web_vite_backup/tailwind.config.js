/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg:     "#070b12",
        bg2:    "#0b1220",
        bg3:    "#0f1a2e",
        border: "#1a3050",
        cyan:   "#00d4ff",
        cyan2:  "#0099bb",
        neon:   "#00e676",
        purple: "#7c4dff",
        red:    "#ff5252",
        dim:    "#7ea8d4",
      },
      fontFamily: { mono: ["Courier New", "monospace"] },
    },
  },
  plugins: [],
}
