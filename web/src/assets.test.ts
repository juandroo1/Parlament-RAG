// @vitest-environment node
// Logo, Favicon, App-Icon und Web-Manifest (AK-8.3, Task 7.1).
import { existsSync, readFileSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const WEB = fileURLToPath(new URL("..", import.meta.url));
const HTML = readFileSync(`${WEB}index.html`, "utf-8");
const MANIFEST = JSON.parse(
  readFileSync(`${WEB}public/manifest.webmanifest`, "utf-8"),
) as {
  icons: { src: string; sizes: string; type: string }[];
  theme_color: string;
  background_color: string;
};

/** Breite und Höhe aus dem IHDR-Block einer PNG-Datei. */
function pngSize(path: string): [number, number] {
  const data = readFileSync(path);
  expect(data.subarray(1, 4).toString("ascii")).toBe("PNG");
  return [data.readUInt32BE(16), data.readUInt32BE(20)];
}

function publicFile(href: string): string {
  return `${WEB}public${href}`;
}

describe("Icons und Manifest", () => {
  it("verlinkt Favicon, Apple-Touch-Icon und Manifest, und die Dateien existieren", () => {
    const hrefs = [
      ...HTML.matchAll(
        /<link rel="(?:icon|apple-touch-icon|manifest)"[^>]*href="([^"]+)"/g,
      ),
    ].map((match) => match[1]);
    expect(hrefs).toEqual([
      "/favicon-32.png",
      "/apple-touch-icon.png",
      "/manifest.webmanifest",
    ]);
    for (const href of hrefs)
      expect(existsSync(publicFile(href)), href).toBe(true);
  });

  it("hat Icons in den angegebenen Grössen", () => {
    expect(pngSize(publicFile("/favicon-32.png"))).toEqual([32, 32]);
    expect(pngSize(publicFile("/apple-touch-icon.png"))).toEqual([180, 180]);
    expect(MANIFEST.icons.map((icon) => icon.sizes)).toEqual([
      "192x192",
      "512x512",
    ]);
    for (const icon of MANIFEST.icons) {
      const side = Number(icon.sizes.split("x")[0]);
      expect(pngSize(publicFile(icon.src))).toEqual([side, side]);
    }
  });

  it("nimmt die Farben des Logos", () => {
    expect(MANIFEST.theme_color).toBe("#0f243f");
    expect(MANIFEST.background_color).toBe("#ffffff");
  });
});

describe("robots.txt", () => {
  it("erlaubt Suchmaschinen die Startseite (Lighthouse SEO, Task 7.7)", () => {
    const robots = readFileSync(`${WEB}public/robots.txt`, "utf-8");
    expect(robots).toMatch(/^User-agent: \*$/m);
    expect(robots).toMatch(/^Allow: \/$/m);
  });
});

describe("Logo der Kopfzeile", () => {
  it.each(["light", "dark"])(
    "liegt als kleine WebP- und PNG-Datei vor (%s)",
    (name) => {
      for (const ext of ["webp", "png"]) {
        const path = `${WEB}src/assets/logo-${name}.${ext}`;
        expect(statSync(path).size).toBeLessThan(20_000);
      }
      expect(pngSize(`${WEB}src/assets/logo-${name}.png`)[1]).toBe(104);
    },
  );
});
