// @vitest-environment node
// Kontraste der Design-Tokens nach WCAG 2.2 (AK-9.4, AK-13.4).
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const CSS = readFileSync(
  fileURLToPath(new URL("./theme.css", import.meta.url)),
  "utf-8",
);

type Tokens = Record<string, string>;

function block(selector: string): Tokens {
  const start = CSS.indexOf(`${selector} {`);
  if (start < 0) throw new Error(`Block ${selector} fehlt`);
  const body = CSS.slice(start, CSS.indexOf("}", start));
  return Object.fromEntries(
    [...body.matchAll(/--fdp-([\w-]+):\s*(#[0-9a-f]{6});/gi)].map(
      ([, name, value]) => [name, value.toLowerCase()],
    ),
  );
}

const MODES: Record<string, Tokens> = {
  hell: block(":root"),
  dunkel: block(':root[data-theme="dark"]'),
};

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [light, dark] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (light + 0.05) / (dark + 0.05);
}

// [Vordergrund, Hintergrund]: Text braucht 4.5:1, Bedienelemente und Fokusring 3:1.
const TEXT: [string, string][] = [
  ["text", "bg"],
  ["text", "surface"],
  ["text", "surface-2"],
  ["text", "warn-bg"],
  ["muted", "bg"],
  ["muted", "surface"],
  ["muted", "surface-2"],
  ["accent-text", "bg"],
  ["accent-text", "surface"],
  ["accent-text", "cite-bg"],
  ["on-primary", "primary"],
  ["error-text", "error-bg"],
];
const CONTROLS: [string, string][] = [
  ["input-border", "bg"],
  ["input-border", "surface"],
  ["accent", "bg"],
  ["accent", "surface"],
  ["primary", "bg"],
  ["primary", "surface"],
];

describe("Design-Tokens", () => {
  it("rechnet Kontraste wie WCAG", () => {
    expect(contrast("#000000", "#ffffff")).toBeCloseTo(21, 5);
    expect(contrast("#777777", "#ffffff")).toBeCloseTo(4.48, 2);
  });

  it("definiert in beiden Modi dieselben Tokens", () => {
    expect(Object.keys(MODES.dunkel).sort()).toEqual(
      Object.keys(MODES.hell).sort(),
    );
    expect(Object.keys(MODES.hell).length).toBeGreaterThanOrEqual(17);
  });

  it("hat für den dunklen Modus nach System und per data-theme dieselben Werte", () => {
    expect(block(':root:not([data-theme="light"])')).toEqual(MODES.dunkel);
  });

  for (const [mode, tokens] of Object.entries(MODES)) {
    it.each(TEXT)(`${mode}: Text %s auf %s mindestens 4.5:1`, (fg, bg) => {
      expect(contrast(tokens[fg], tokens[bg])).toBeGreaterThanOrEqual(4.5);
    });
    it.each(CONTROLS)(
      `${mode}: Bedienelement %s auf %s mindestens 3:1`,
      (fg, bg) => {
        expect(contrast(tokens[fg], tokens[bg])).toBeGreaterThanOrEqual(3);
      },
    );
  }
});
