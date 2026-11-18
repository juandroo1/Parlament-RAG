// @vitest-environment node
// Komponenten verwenden nur die Farb-Tokens aus theme.css, keine festen Farben (AK-8.1).
import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const SRC = fileURLToPath(new URL(".", import.meta.url));
const FILES = readdirSync(SRC, { recursive: true, encoding: "utf-8" }).filter(
  (file) => file.endsWith(".tsx") && !file.endsWith(".test.tsx"),
);

const PALETTE =
  /\b(?:bg|text|border|ring|outline|fill|stroke|decoration|divide|from|via|to|shadow|accent|caret)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|white|black)\b/g;
const HEX = /#[0-9a-fA-F]{6}\b|\brgba?\(/g;

describe("Farben nur aus Tokens", () => {
  it("findet die Komponenten", () => {
    expect(FILES.length).toBeGreaterThanOrEqual(6);
  });

  it.each(FILES)(
    "%s enthält keine Tailwind-Palettenfarben und keine Farbwerte",
    (file) => {
      const source = readFileSync(`${SRC}${file}`, "utf-8");
      expect(source.match(PALETTE) ?? []).toEqual([]);
      expect(source.match(HEX) ?? []).toEqual([]);
    },
  );
});
