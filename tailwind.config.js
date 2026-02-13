/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        flowstorm: {
          bg: "#0f1117",
          surface: "#1a1d27",
          border: "#2a2d3a",
          primary: "#6366f1",
          secondary: "#8b5cf6",
          success: "#22c55e",
          warning: "#f59e0b",
          danger: "#ef4444",
          text: "#e2e8f0",
          muted: "#94a3b8",
        },
      },
    },
  },
  plugins: [],
};
