/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      screens: {
        xs: "370px",
      },
      colors: {
        /* shadcn/ui semantic tokens */
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },

        /* TradingView semantic tokens (legacy utility names kept, re-pointed) */
        gold: {
          DEFAULT: "var(--tv-accent)",
          deep:    "var(--tv-accent-hover)",
          dim:     "var(--tv-text-3)",
        },
        ink: {
          DEFAULT: "var(--tv-text-1)",
          muted:   "var(--tv-text-2)",
          faint:   "var(--tv-text-3)",
        },
        bg: {
          deep: "var(--tv-bg)",
          DEFAULT: "var(--tv-bg)",
          soft: "var(--tv-surface)",
          card: "var(--tv-surface)",
        },
        surface: {
          DEFAULT: "var(--tv-surface)",
          "2":     "var(--tv-surface-2)",
        },
        line:  "var(--tv-border)",
        up:    "var(--tv-up)",
        down:  "var(--tv-down)",
        warn:  "var(--tv-warn)",
        market: {
          up:   "var(--tv-up)",
          down: "var(--tv-down)",
        },

        /* App custom color tokens */
        myBlue1:   "rgba(var(--myBlue1))",
        myBlue2:   "rgba(var(--myBlue2))",
        myCyan1:   "rgba(var(--myCyan1))",
        myPurple1: "rgba(var(--myPurple1))",
        myPurple2: "rgba(var(--myPurple2))",
        myText1:   "rgba(var(--myText1))",
        myGray1:   "rgba(var(--myGray1))",
        myGray2:   "rgba(var(--myGray2))",
        myGreen1:  "rgba(var(--myGreen1))",
        myRed1:    "rgba(var(--myRed1))",
        myRed2:    "rgba(var(--myRed2))",
        myYellow1: "rgba(var(--myYellow1))",
        myYellow2: "rgba(var(--myYellow2))",
        tableBg1:  "rgba(var(--table-bg-1))",
        mainBg:    "rgba(var(--main-bg))",
        myPink1:   "rgba(var(--myPink1))",
        myOrange1: "rgba(var(--myOrange1))",
      },
      fontFamily: {
        sans:    ["-apple-system", "'Segoe UI'", "Roboto", "Ubuntu", "sans-serif"],
        display: ["-apple-system", "'Segoe UI'", "Roboto", "Ubuntu", "sans-serif"],
        serif:   ["-apple-system", "'Segoe UI'", "Roboto", "Ubuntu", "sans-serif"],
        accent:  ["-apple-system", "'Segoe UI'", "Roboto", "Ubuntu", "sans-serif"],
        mono:    ["var(--font-mono)", "ui-monospace", "SF Mono", "Menlo", "monospace"],
      },
      borderRadius: {
        lg: "8px",
        md: "6px",
        sm: "4px",
        DEFAULT: "6px",
      },
      keyframes: {
        "accordion-down": {
          from: { height: 0 },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: 0 },
        },
        "caret-blink": {
          "0%,70%,100%": { opacity: "1" },
          "20%,50%": { opacity: "0" },
        },
        "pulse-dot": {
          "0%,100%": { opacity: "1" },
          "50%": { opacity: "0.3" },
        },
        "reveal-up": {
          from: { opacity: "0", transform: "translateY(16px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "marquee": {
          from: { transform: "translateX(0)" },
          to:   { transform: "translateX(-50%)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "caret-blink": "caret-blink 1.25s ease-out infinite",
        "pulse-dot": "pulse-dot 2s ease-in-out infinite",
        "reveal-up": "reveal-up 0.85s ease forwards",
        "marquee": "marquee 60s linear infinite",
      },
      boxShadow: {
        gold:       "0 4px 16px -8px rgba(0,0,0,.4)",
        "gold-sm":  "0 2px 8px -4px rgba(0,0,0,.3)",
        "gold-glow":"none",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
