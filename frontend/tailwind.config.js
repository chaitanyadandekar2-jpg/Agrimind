/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        soil: {
          50: "#f6f1ea",
          100: "#e9dcc9",
          300: "#c9a877",
          500: "#8a5a34",
          700: "#5c3a20",
          900: "#2e1d10",
        },
        leaf: {
          400: "#7fae4f",
          500: "#5c8f37",
          600: "#456b28",
          700: "#31501d",
        },
        wheat: {
          400: "#e3b23c",
        },
      },
      fontFamily: {
        display: ["'Fraunces'", "serif"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
    },
  },
  plugins: [],
}
