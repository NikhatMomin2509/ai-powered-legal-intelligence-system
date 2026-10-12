/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        serif: ["'Source Serif 4'", "Georgia", "serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      colors: {
        ink: {
          950: "#080c14",
          900: "#0d131f",
          850: "#131a2a",
          800: "#1a2337",
          700: "#27344f",
          600: "#3d4e70",
          500: "#64748b",
          400: "#94a3b8",
          300: "#cbd5e1",
          200: "#e2e8f0",
          100: "#f1f5f9",
          50: "#f8fafc",
        },
        statute: {
          DEFAULT: "#d97706",
          light: "#f59e0b",
          border: "rgba(217, 119, 6, 0.25)",
          bg: "rgba(217, 119, 6, 0.05)",
        },
        precedent: {
          DEFAULT: "#6366f1",
          light: "#818cf8",
          border: "rgba(99, 102, 241, 0.25)",
          bg: "rgba(99, 102, 241, 0.05)",
        },
        risk: {
          low: "#10b981",
          medium: "#f59e0b",
          high: "#f43f5e",
        },
        authority: "#6366f1",
      },
      boxShadow: {
        glow: "0 0 24px rgba(16, 185, 129, 0.25)",
        "glow-rose": "0 0 24px rgba(244, 63, 94, 0.25)",
        "glow-amber": "0 0 24px rgba(245, 158, 11, 0.25)",
        "glow-indigo": "0 0 24px rgba(99, 102, 241, 0.25)",
        card: "0 1px 3px rgba(0, 0, 0, 0.3), 0 4px 12px rgba(0, 0, 0, 0.2)",
      },
      keyframes: {
        pulseSoft: {
          "0%, 100%": { opacity: 1 },
          "50%": { opacity: 0.4 },
        },
      },
      animation: {
        "pulse-soft": "pulseSoft 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
