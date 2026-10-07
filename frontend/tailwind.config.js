/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        serif: ["'Source Serif 4'", "Georgia", "serif"],
      },
      colors: {
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
