// Sprache der Oberfläche (Spec 002, US-10; Plan 002, Abschnitt 5).

import { de, type Messages } from "./de";
import { fr } from "./fr";

export type Language = "de" | "fr";

export const LANGUAGES: Language[] = ["de", "fr"];
export const MESSAGES: Record<Language, Messages> = { de, fr };
export const STORAGE_KEY = "fdp-lang";

function isLanguage(value: unknown): value is Language {
  return value === "de" || value === "fr";
}

/**
 * Startsprache (AK-10.2): gespeicherte Wahl, sonst die erste Browsersprache, die Deutsch oder
 * Französisch ist, sonst Deutsch. Ohne Speicher (privates Fenster) zählt nur der Browser.
 */
export function readLanguage(): Language {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (isLanguage(saved)) return saved;
  } catch {
    // weiter mit der Sprache des Browsers
  }
  const browser = navigator.languages?.length
    ? navigator.languages
    : [navigator.language];
  for (const tag of browser) {
    const base = tag?.slice(0, 2).toLowerCase();
    if (isLanguage(base)) return base;
  }
  return "de";
}

export function saveLanguage(language: Language): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // Ohne Speicher gilt die Wahl bis zum Neuladen.
  }
}
