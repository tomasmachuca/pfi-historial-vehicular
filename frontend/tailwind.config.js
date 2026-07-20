/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4fb",
          100: "#d8e6f5",
          200: "#b4cdea",
          300: "#85acdb",
          400: "#5688c7",
          500: "#2f66ad",
          600: "#23508d",
          700: "#1b3f70",
          800: "#16325a",
          900: "#102440",
          950: "#0a1729",
        },
        // Celeste como guiño a la bandera, para acentos sobre fondo oscuro
        celeste: {
          300: "#9cc6e8",
          400: "#74acdf",
          500: "#4f95d3",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgb(16 36 64 / 0.04), 0 4px 16px -4px rgb(16 36 64 / 0.08)",
        lift: "0 2px 4px rgb(16 36 64 / 0.06), 0 12px 32px -8px rgb(16 36 64 / 0.14)",
      },
      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.5s cubic-bezier(0.22, 1, 0.36, 1) both",
      },
    },
  },
  plugins: [],
};
