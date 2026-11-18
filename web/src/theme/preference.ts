// Dunkler Modus (Spec 002, US-9; Plan 002, Abschnitt 4). Dieselbe Logik steht als Inline-Script im
// <head> von index.html, damit beim Laden nichts aufblitzt; index.test.ts prüft, dass beide
// übereinstimmen.

export type ThemePreference = "system" | "light" | "dark";
export type Theme = "light" | "dark";

export const STORAGE_KEY = "fdp-theme";
export const DARK_QUERY = "(prefers-color-scheme: dark)";
/** Farbe der Browserleiste (meta theme-color) je Modus, wie der Hintergrund der Seite. */
export const THEME_COLORS: Record<Theme, string> = {
  light: "#ffffff",
  dark: "#121622",
};

/** Gespeicherte Wahl; ohne Speicher (privates Fenster) oder mit ungültigem Wert `system`. */
export function readPreference(): ThemePreference {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    return saved === "light" || saved === "dark" ? saved : "system";
  } catch {
    return "system";
  }
}

/** Speichert die Wahl; `system` löscht den Eintrag. Fehler des Speichers werden ignoriert. */
export function savePreference(preference: ThemePreference): void {
  try {
    if (preference === "system") window.localStorage.removeItem(STORAGE_KEY);
    else window.localStorage.setItem(STORAGE_KEY, preference);
  } catch {
    // Ohne Speicher gilt die Wahl nur bis zum Neuladen (AK-9.2).
  }
}

export function systemPrefersDark(): boolean {
  return window.matchMedia?.(DARK_QUERY).matches ?? false;
}

export function resolveTheme(
  preference: ThemePreference,
  systemDark: boolean,
): Theme {
  if (preference === "system") return systemDark ? "dark" : "light";
  return preference;
}

/**
 * Setzt `data-theme` auf <html> und die Farbe der Browserleiste. Bei `system` bekommen die beiden
 * meta-Tags wieder ihre Farbe je Media Query, sonst beide die Farbe des gewählten Modus.
 */
export function applyTheme(
  preference: ThemePreference,
  theme: Theme,
  doc: Document = document,
): void {
  doc.documentElement.setAttribute("data-theme", theme);
  for (const meta of doc.querySelectorAll<HTMLMetaElement>(
    'meta[name="theme-color"]',
  )) {
    const own: Theme = (meta.getAttribute("media") ?? "").includes("dark")
      ? "dark"
      : "light";
    meta.setAttribute(
      "content",
      THEME_COLORS[preference === "system" ? own : theme],
    );
  }
}
