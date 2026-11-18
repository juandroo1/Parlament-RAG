// Erzeugt Logo und Icons der Web-UI aus den Originalen in diesem Ordner (Task 7.1).
// Einmalig von Hand ausführen, nicht im Build; Anleitung in README.md.

import { createRequire } from "node:module";
import { mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const web = join(here, "..", "..", "web");
// sharp liegt nur vorübergehend in web/node_modules (npm install --no-save).
const sharp = createRequire(join(web, "package.json"))("sharp");

const LOGOS = {
  light: join(here, "frag-das-parlament-logo.jpeg"),
  dark: join(here, "frag-das-parlament-logo-dark.jpeg"),
};
const ASSETS = join(web, "src", "assets");
const PUBLIC = join(web, "public");

// Kopfzeile: Inhalt des Logos 52 px hoch (Plan 002, Abschnitt 8), doppelte Auflösung.
const HEADER_HEIGHT = 2 * 52;
// Abweichung vom Hintergrund, ab der ein Pixel zum Logo zählt (JPEG-Artefakte liegen darunter).
const THRESHOLD = 48;
// Spalten ohne Inhalt, die Signet und Schriftzug trennen.
const GAP = 24;

async function load(path) {
  const { data, info } = await sharp(path).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  return { data, width: info.width, height: info.height };
}

/** Hintergrundfarbe (Ecke) und je Spalte bzw. Zeile, ob Inhalt vorkommt. */
function analyse({ data, width, height }) {
  const bg = [data[0], data[1], data[2]];
  const columns = new Array(width).fill(false);
  const rows = new Array(height).fill(false);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const i = (y * width + x) * 3;
      const diff = Math.max(
        Math.abs(data[i] - bg[0]),
        Math.abs(data[i + 1] - bg[1]),
        Math.abs(data[i + 2] - bg[2]),
      );
      if (diff > THRESHOLD) {
        columns[x] = true;
        rows[y] = true;
      }
    }
  }
  return { bg, columns, rows };
}

function bounds(flags) {
  return [flags.indexOf(true), flags.lastIndexOf(true)];
}

/** Rechter Rand des Signets: erste Lücke von GAP leeren Spalten nach dem ersten Inhalt. */
function signetRight(columns, left) {
  let empty = 0;
  for (let x = left; x < columns.length; x++) {
    empty = columns[x] ? 0 : empty + 1;
    if (empty === GAP) return x - GAP;
  }
  throw new Error("Keine Lücke zwischen Signet und Schriftzug gefunden");
}

function hex([r, g, b]) {
  return "#" + [r, g, b].map((v) => v.toString(16).padStart(2, "0")).join("");
}

async function headerLogo(name, path) {
  const image = await load(path);
  const { bg, columns, rows } = analyse(image);
  const [left, right] = bounds(columns);
  const [top, bottom] = bounds(rows);
  const pad = Math.round((bottom - top) * 0.04);
  const region = {
    left: Math.max(0, left - pad),
    top: Math.max(0, top - pad),
    width: Math.min(image.width, right + pad + 1) - Math.max(0, left - pad),
    height: Math.min(image.height, bottom + pad + 1) - Math.max(0, top - pad),
  };
  const base = sharp(path).extract(region).resize({ height: HEADER_HEIGHT });
  await base.clone().webp({ quality: 90 }).toFile(join(ASSETS, `logo-${name}.webp`));
  await base.clone().png({ compressionLevel: 9, palette: true }).toFile(join(ASSETS, `logo-${name}.png`));
  const width = Math.round((region.width * HEADER_HEIGHT) / region.height);
  console.log(`logo-${name}: Ausschnitt ${JSON.stringify(region)}, Hintergrund ${hex(bg)}, ${width}×${HEADER_HEIGHT}`);
  return { left, top, bottom, columns, bg };
}

async function icons(path, found) {
  const right = signetRight(found.columns, found.left);
  const size = Math.max(right - found.left, found.bottom - found.top);
  const side = Math.round(size * 1.24);
  const cx = Math.round((found.left + right) / 2);
  const cy = Math.round((found.top + found.bottom) / 2);
  const region = { left: cx - side / 2, top: cy - side / 2, width: side, height: side };
  for (const key of Object.keys(region)) region[key] = Math.round(region[key]);
  const signet = sharp(path).extract(region);
  const outputs = [
    ["favicon-32.png", 32],
    ["apple-touch-icon.png", 180],
    ["icon-192.png", 192],
    ["icon-512.png", 512],
  ];
  for (const [file, px] of outputs) {
    await signet.clone().resize(px, px).png({ compressionLevel: 9, palette: true }).toFile(join(PUBLIC, file));
  }
  console.log(`Icons: Signet ${JSON.stringify(region)}`);
}

await mkdir(ASSETS, { recursive: true });
await mkdir(PUBLIC, { recursive: true });
const light = await headerLogo("light", LOGOS.light);
await headerLogo("dark", LOGOS.dark);
await icons(LOGOS.light, light);
