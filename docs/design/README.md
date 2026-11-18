# Design-Quellen

Originale des Logos und das Skript, das daraus die Dateien der Web-UI erzeugt (Spec 002, Task 7.1).

| Datei | Inhalt |
|---|---|
| `frag-das-parlament-logo.jpeg` | Logo hell, 1774 × 887 px, weisser Hintergrund |
| `frag-das-parlament-logo-dark.jpeg` | Logo dunkel, 1774 × 887 px, Hintergrund `#121622` |
| `make-assets.mjs` | erzeugt Logo und Icons für `web/` |

## Erzeugte Dateien

| Datei | Zweck |
|---|---|
| `web/src/assets/logo-light.webp`, `.png` | Logo in der Kopfzeile, hell; auf den Inhalt zugeschnitten, 104 px hoch (doppelte Auflösung für 52 px) |
| `web/src/assets/logo-dark.webp`, `.png` | dasselbe für den dunklen Modus |
| `web/public/favicon-32.png` | Favicon |
| `web/public/apple-touch-icon.png` | Icon auf dem Homescreen (iOS), 180 px |
| `web/public/icon-192.png`, `icon-512.png` | Icons im Web-Manifest |

Das Skript findet den Rand des Logos selbst: Ein Pixel zählt zum Logo, wenn es um mehr als 48 Stufen vom Hintergrund (Farbe der Ecke) abweicht. Das Signet für die Icons endet bei der ersten Lücke von 24 leeren Spalten vor dem Schriftzug. Die Icons nehmen das helle Logo mit weissem Hintergrund.

## Neu erzeugen

Nur nötig, wenn sich ein Original ändert. `sharp` wird dafür nur vorübergehend installiert und kommt weder in `package.json` noch ins Build:

```bash
cd web
npm install --no-save sharp@0.35.5
node ../docs/design/make-assets.mjs
npm ci                     # entfernt sharp wieder
```

Danach die erzeugten Dateien ansehen und committen; `web/src/assets.test.ts` prüft Grössen und Verweise.
