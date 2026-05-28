import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        border:       "hsl(var(--border))",
        "border-strong": "hsl(var(--border-strong))",
        input:        "hsl(var(--input))",
        ring:         "hsl(var(--ring))",
        background:   "hsl(var(--background))",
        surface:      "hsl(var(--surface))",
        "surface-raised": "hsl(var(--surface-raised))",
        foreground:   "hsl(var(--foreground))",
        "foreground-muted":   "hsl(var(--foreground-muted))",
        "foreground-subtle":  "hsl(var(--foreground-subtle))",
        primary: {
          DEFAULT:    "hsl(var(--primary))",
          light:      "hsl(var(--primary-light))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT:    "hsl(var(--secondary))",
          light:      "hsl(var(--secondary-light))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        accent: {
          DEFAULT:    "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        success: {
          DEFAULT:    "hsl(var(--success))",
          light:      "hsl(var(--success-light))",
        },
        warning: {
          DEFAULT:    "hsl(var(--warning))",
          light:      "hsl(var(--warning-light))",
        },
        danger: {
          DEFAULT:    "hsl(var(--danger))",
          light:      "hsl(var(--danger-light))",
        },
        muted: {
          DEFAULT:    "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        card: {
          DEFAULT:    "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
          border:     "hsl(var(--card-border))",
        },
        sidebar: {
          bg:          "hsl(var(--sidebar-bg))",
          active:      "hsl(var(--sidebar-active))",
          text:        "hsl(var(--sidebar-text))",
          "text-active": "hsl(var(--sidebar-text-active))",
          hover:       "hsl(var(--sidebar-hover))",
          border:      "hsl(var(--sidebar-border))",
        },
      },
      borderRadius: {
        DEFAULT: "var(--radius)",
        sm:      "var(--radius-sm)",
        md:      "var(--radius)",
        lg:      "var(--radius-lg)",
        xl:      "1.25rem",
        "2xl":   "1.5rem",
      },
      boxShadow: {
        card:   "0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)",
        "card-md": "0 4px 12px rgba(0,0,0,0.1), 0 2px 4px rgba(0,0,0,0.06)",
        "card-lg": "0 8px 24px rgba(0,0,0,0.12), 0 3px 8px rgba(0,0,0,0.08)",
        glow:   "0 0 20px rgba(21,101,192,0.25)",
        "glow-teal": "0 0 20px rgba(0,168,142,0.25)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
