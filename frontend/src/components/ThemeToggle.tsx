import { useEffect, useState } from "react";

type Theme = "light" | "dark";

const STORAGE_KEY = "orochi-theme";

function resolveInitialTheme(): Theme {
  if (typeof window === "undefined") return "light";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  const prefersDark =
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches;
  return prefersDark ? "dark" : "light";
}

function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(resolveInitialTheme);

  useEffect(() => {
    applyTheme(theme);
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      /* ignore storage failures (private mode, etc.) */
    }
  }, [theme]);

  const isDark = theme === "dark";
  const toggle = () => setTheme((t) => (t === "dark" ? "light" : "dark"));

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={toggle}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      title={isDark ? "Switch to light mode" : "Switch to dark mode"}
      style={{
        appearance: "none",
        cursor: "pointer",
        width: 38,
        height: 38,
        display: "grid",
        placeItems: "center",
        fontSize: "1.05rem",
        lineHeight: 1,
        color: "var(--ink-soft)",
        background: "var(--surface)",
        border: "1px solid var(--line-strong)",
        borderRadius: 12,
        boxShadow: "var(--shadow-sm)",
        transition:
          "color 0.2s, background 0.2s, border-color 0.2s, transform 0.12s var(--ease)",
      }}
    >
      <span aria-hidden="true">{isDark ? "☀️" : "\u{1F319}"}</span>
    </button>
  );
}
