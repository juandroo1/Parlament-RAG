import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api";
import { de } from "./de";
import { errorText } from "./errors";
import { fr } from "./fr";
import { readLanguage, saveLanguage, STORAGE_KEY } from "./language";

/** Alle Pfade zu Blättern (Texte, Funktionen, Listen) eines Wörterbuchs. */
function paths(value: unknown, prefix = ""): string[] {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return Object.entries(value).flatMap(([key, child]) =>
      paths(child, prefix ? `${prefix}.${key}` : key),
    );
  }
  return [prefix];
}

function leaves(value: unknown): unknown[] {
  if (Array.isArray(value)) return value.flatMap(leaves);
  if (value && typeof value === "object")
    return Object.values(value).flatMap(leaves);
  return [value];
}

afterEach(() => vi.restoreAllMocks());

describe("Wörterbücher", () => {
  it("haben dieselben Schlüssel auf Deutsch und Französisch (AK-10.5)", () => {
    expect(paths(fr).sort()).toEqual(paths(de).sort());
    expect(fr.form.exampleQuestions).toHaveLength(
      de.form.exampleQuestions.length,
    );
  });

  it("enthalten keine leeren Texte", () => {
    for (const dictionary of [de, fr]) {
      for (const leaf of leaves(dictionary)) {
        if (typeof leaf === "string") expect(leaf.trim()).not.toBe("");
        else expect(typeof leaf).toBe("function");
      }
    }
  });

  it("übersetzt Texte mit Werten", () => {
    expect(de.answer.badge(1)).toBe("KI-Antwort aus 1 Quelle");
    expect(de.answer.badge(3)).toBe("KI-Antwort aus 3 Quellen");
    expect(fr.answer.badge(1)).toBe("Réponse IA tirée d'une source");
    expect(fr.answer.badge(3)).toBe("Réponse IA tirée de 3 sources");
    expect(fr.form.activeFilters(2)).toBe("2 actifs");
  });

  it("zeigt Beispielfragen auch in der anderen Sprache (sprachübergreifende Suche)", () => {
    for (const dictionary of [de, fr]) {
      const langs = new Set(
        dictionary.form.exampleQuestions.map((example) => example.lang),
      );
      expect(langs).toEqual(new Set(["de", "fr"]));
    }
  });
});

describe("Startsprache (AK-10.2)", () => {
  const browser = (languages: string[]) =>
    vi.spyOn(navigator, "languages", "get").mockReturnValue(languages);

  it("nimmt die gespeicherte Wahl", () => {
    browser(["de-CH"]);
    saveLanguage("fr");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("fr");
    expect(readLanguage()).toBe("fr");
  });

  it("nimmt sonst die erste passende Sprache des Browsers", () => {
    browser(["fr-CH", "de"]);
    expect(readLanguage()).toBe("fr");
    browser(["en-US", "fr"]);
    expect(readLanguage()).toBe("fr");
    browser(["it-CH", "de-CH"]);
    expect(readLanguage()).toBe("de");
  });

  it("nimmt Deutsch, wenn nichts passt oder der Wert ungültig ist", () => {
    browser(["en-US", "it"]);
    window.localStorage.setItem(STORAGE_KEY, "it");
    expect(readLanguage()).toBe("de");
  });

  it("funktioniert ohne Speicher", () => {
    browser(["fr-CH"]);
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("blockiert", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("blockiert", "SecurityError");
    });
    expect(readLanguage()).toBe("fr");
    expect(() => saveLanguage("de")).not.toThrow();
  });
});

describe("Fehlermeldungen der Oberfläche", () => {
  it("formuliert Fehler der App in der gewählten Sprache", () => {
    const network = new ApiError("x", null, "network");
    expect(errorText(network, de)).toBe(
      "Die API ist nicht erreichbar. Läuft der Server?",
    );
    expect(errorText(network, fr)).toMatch(/^L'API n'est pas joignable/);
    const invalid = new ApiError("x", 422, "validation", "String too short");
    expect(errorText(invalid, fr)).toBe(
      "La saisie n'est pas valable : String too short",
    );
    expect(errorText(new ApiError("x", 502), fr)).toBe(
      "La requête a échoué (HTTP 502).",
    );
    expect(errorText(new Error("kaputt"), fr)).toBe(
      "Erreur inattendue. Veuillez réessayer.",
    );
  });

  it("zeigt Meldungen der API vorerst unverändert (Task 7.5 übersetzt sie)", () => {
    const fromApi = new ApiError(
      "Zu viele Fragen",
      429,
      "http",
      "Zu viele Fragen",
    );
    expect(errorText(fromApi, fr)).toBe("Zu viele Fragen");
  });
});
