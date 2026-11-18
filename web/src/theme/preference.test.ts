import { afterEach, describe, expect, it, vi } from "vitest";
import { systemTheme } from "../test/matchMedia";
import {
  applyTheme,
  readPreference,
  resolveTheme,
  savePreference,
  STORAGE_KEY,
  systemPrefersDark,
} from "./preference";

function themeMetas() {
  document.head.innerHTML =
    '<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">' +
    '<meta name="theme-color" content="#121622" media="(prefers-color-scheme: dark)">';
  return [
    ...document.head.querySelectorAll<HTMLMetaElement>(
      'meta[name="theme-color"]',
    ),
  ];
}

afterEach(() => {
  vi.restoreAllMocks();
  document.head.innerHTML = "";
});

describe("Wahl speichern und lesen", () => {
  it("liest gespeicherte Wahl, sonst system", () => {
    expect(readPreference()).toBe("system");
    savePreference("dark");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("dark");
    expect(readPreference()).toBe("dark");
    savePreference("system");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("behandelt ungültige Werte als system", () => {
    window.localStorage.setItem(STORAGE_KEY, "blau");
    expect(readPreference()).toBe("system");
  });

  it("funktioniert ohne Speicher (privates Fenster)", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("blockiert", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("blockiert", "SecurityError");
    });
    expect(readPreference()).toBe("system");
    expect(() => savePreference("dark")).not.toThrow();
  });
});

describe("Modus bestimmen und setzen", () => {
  it("folgt bei system der Systemeinstellung", () => {
    expect(resolveTheme("system", false)).toBe("light");
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("light", true)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
    systemTheme.setDark(true);
    expect(systemPrefersDark()).toBe(true);
  });

  it("setzt data-theme und die Farbe der Browserleiste", () => {
    const [light, dark] = themeMetas();
    applyTheme("dark", "dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect([light.content, dark.content]).toEqual(["#121622", "#121622"]);

    applyTheme("light", "light");
    expect([light.content, dark.content]).toEqual(["#ffffff", "#ffffff"]);

    // Zurück zu system: jedes meta-Tag wieder mit seiner eigenen Farbe.
    applyTheme("system", "dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect([light.content, dark.content]).toEqual(["#ffffff", "#121622"]);
  });
});
