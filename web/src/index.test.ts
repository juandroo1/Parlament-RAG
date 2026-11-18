// Inline-Script gegen Aufblitzen im <head> von index.html (AK-9.3): Es muss für jede Kombination
// aus gespeicherter Wahl und Systemeinstellung dasselbe ergeben wie src/theme/preference.ts.
import { readFileSync } from "node:fs";
import { afterEach, describe, expect, it, vi } from "vitest";
import { systemTheme } from "./test/matchMedia";
import {
  applyTheme,
  resolveTheme,
  STORAGE_KEY,
  type ThemePreference,
} from "./theme/preference";

const HTML = readFileSync(`${process.cwd()}/index.html`, "utf-8");
const HEAD = HTML.slice(HTML.indexOf("<head>") + 6, HTML.indexOf("</head>"));
const SCRIPT = /<script>([\s\S]*?)<\/script>/.exec(HEAD)?.[1] ?? "";
const METAS = [...HEAD.matchAll(/<meta\s+name="theme-color"[^>]*\/?>/g)]
  .map((m) => m[0])
  .join("");

function metaContents(): string[] {
  return [
    ...document.head.querySelectorAll<HTMLMetaElement>(
      'meta[name="theme-color"]',
    ),
  ].map((meta) => meta.content);
}

function runInlineScript() {
  document.head.innerHTML = METAS;
  document.documentElement.removeAttribute("data-theme");
  new Function(SCRIPT)();
  return {
    theme: document.documentElement.dataset.theme,
    metas: metaContents(),
  };
}

function expected(preference: ThemePreference, systemDark: boolean) {
  document.head.innerHTML = METAS;
  applyTheme(preference, resolveTheme(preference, systemDark));
  return {
    theme: document.documentElement.dataset.theme,
    metas: metaContents(),
  };
}

afterEach(() => {
  vi.restoreAllMocks();
  document.head.innerHTML = "";
});

describe("Script gegen Aufblitzen", () => {
  it("steht im <head> vor dem Stylesheet und dem App-Script", () => {
    expect(SCRIPT).toContain(STORAGE_KEY);
    expect(METAS.match(/theme-color/g)).toHaveLength(2);
    expect(HTML.indexOf("<script>")).toBeLessThan(
      HTML.indexOf('type="module"'),
    );
  });

  const cases: [string | null, boolean, ThemePreference][] = [
    [null, false, "system"],
    [null, true, "system"],
    ["light", true, "light"],
    ["dark", false, "dark"],
    ["blau", true, "system"],
  ];
  it.each(cases)(
    "gespeichert %s, System dunkel %s: wie preference.ts",
    (saved, dark, preference) => {
      if (saved) window.localStorage.setItem(STORAGE_KEY, saved);
      systemTheme.setDark(dark);
      expect(runInlineScript()).toEqual(expected(preference, dark));
    },
  );

  it("funktioniert ohne Speicher", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("blockiert", "SecurityError");
    });
    systemTheme.setDark(true);
    expect(runInlineScript().theme).toBe("dark");
  });
});
