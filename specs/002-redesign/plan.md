# Plan 002 – Redesign der Web-UI

Wie [Spec 002](spec.md) umgesetzt wird. Architektur, Stack und Leitplanken aus [Plan 001](../001-frag-das-parlament/plan.md) gelten weiter; hier steht nur, was sich an der Web-UI ändert.

## 1. Grundsatz

- Die Änderungen liegen fast nur in `web/`. Das Backend bekommt einzig maschinenlesbare Fehlercodes für übersetzbare Meldungen (Abschnitt 6, AK-10.3).
- Keine neuen Laufzeit-Abhängigkeiten ausser selbst gehosteten Schriften. Übersetzung und Dark Mode sind eigener, kleiner Code statt Bibliotheken.
- Docker bleibt gleich: Der `web`-Container baut die App wie bisher und liefert sie über nginx aus.

## 2. Gewählter Entwurf: Variante A «Klar»

Drei Entwürfe (A «Klar», B «Band», C «Bulletin») wurden als klickbarer Prototyp mit Desktop- und Handy-Ansicht verglichen. Gewählt ist **A** (Entscheidungsprotokoll):

- **Kopfzeile:** Logo links; rechts der Knopf «So funktioniert's», der Umschalter DE/FR und der Umschalter Hell/Dunkel/System. Auf dem Handy werden der Knopf «So funktioniert's» und der Darstellungs-Umschalter zu Symbolknöpfen; die Darstellung wechselt dort mit einem Knopf der Reihe nach System → Hell → Dunkel.
- **Hinweis** «Privates Projekt – keine amtliche Veröffentlichung» als Pille direkt unter der Kopfzeile (AK-8.2).
- **Einstieg:** Titel «Was wurde im Parlament gesagt?» mit kurzer Erklärung, darunter eine Suchkarte: Fragefeld, Beispielfragen, Filter (aufklappbar), Knopf «Fragen». Am Desktop zentriert (Breite rund 760 px), auf dem Handy linksbündig; die Beispielfragen lassen sich dort seitlich wischen.
- **Antwort:** Überschrift mit Hinweis «KI-Antwort aus n Quellen», Antworttext mit Zitaten als rote Nummern-Marken, die zur Quelle springen.
- **Quellen:** Karten mit Nummer, Redner/in, Rolle, Rat und Datum, Textausschnitt und Link zur Originalstelle.
- **Footer:** Quelle, Stand und Download-Datum, Hinweis «keine amtliche Veröffentlichung», Lizenz.
- **«So funktioniert's»:** am Desktop eine Seitenleiste von rechts, auf dem Handy ein Blatt von unten.
- **Farben:** Navy als Hauptfarbe (Text, Knopf «Fragen»), Rot sparsam für Zitate und Links, im Dark Mode Nachtblau als Hintergrund mit hellem Knopf.

## 3. Design-Tokens

Die Farben stehen als CSS-Variablen in `web/src/theme.css`, einmal für hell und einmal für dunkel. Tailwind 4 bildet sie mit `@theme inline` auf eigene Klassen ab (z. B. `bg-surface`, `text-muted`, `text-accent`). Komponenten verwenden nur diese Klassen, keine Farbwerte.

| Token | Hell | Dunkel | Verwendung |
|---|---|---|---|
| `bg` | `#ffffff` | `#121622` | Seite, Kopfzeile (passt zum Hintergrund des Logos) |
| `surface` | `#f4f6f9` | `#1a2131` | Suchkarte, Quellen, Footer |
| `surface-2` | `#e7ecf2` | `#252e43` | Badges |
| `border` | `#d5dde7` | `#34405a` | Rahmen, Trennlinien |
| `input-border` | `#7d8ea3` | `#66779b` | Eingabefelder (3:1 zum Hintergrund) |
| `text` | `#0f243f` | `#f4f5f7` | Text, Überschriften |
| `muted` | `#4b5c71` | `#aab4c5` | Nebentext |
| `primary` / `on-primary` | `#0f243f` / `#ffffff` | `#f4f5f7` / `#121622` | Knopf «Fragen», aktive Umschalter |
| `accent` | `#da2727` | `#e00d0f` | Fokusring, Akzentflächen |
| `accent-text` | `#c42020` | `#ff8a85` | Zitate, Links in Rot |
| `cite-bg` | `#fdecec` | `#3a1d24` | Hintergrund der Zitat-Marken |

Für die Zustände «keine Grundlage» (`warn-bg`, `warn-border`) und Fehler (`error-bg`, `error-border`, `error-text`) gibt es eigene Tokens (Task 7.1). Ein Test rechnet die Kontraste aller Paare aus Text- und Hintergrund-Tokens nach (AK-13.4, AK-9.4).

## 4. Dunkler Modus

- **Präferenz:** `system` (Standard), `light` oder `dark`, gespeichert unter `localStorage["fdp-theme"]`. Jeder Zugriff auf den Speicher steht in `try/catch`; ohne Speicher gilt `system` (AK-9.2).
- **Umsetzung:** Das Attribut `data-theme="light|dark"` auf `<html>` bestimmt die Tokens. Tailwind: `@custom-variant dark (&:where([data-theme=dark], [data-theme=dark] *))`. Bei `system` folgt die Seite `matchMedia("(prefers-color-scheme: dark)")`, auch bei einem Wechsel im laufenden Betrieb (AK-9.1).
- **Kein Aufblitzen:** Ein kleines Inline-Script im `<head>` von `index.html` setzt `data-theme`, bevor die Seite gezeichnet wird (AK-9.3). nginx setzt heute keine Content-Security-Policy; kommt später eine dazu, braucht das Script einen Hash.
- **Logo:** Die Kopfzeile zeigt je nach Modus die helle oder die dunkle Logodatei.

## 5. Sprache der Oberfläche

- **Eigenes Modul** `web/src/i18n/`: `de.ts` ist die Quelle aller Texte; `fr.ts` muss denselben Typ erfüllen. Fehlt in `fr.ts` ein Schlüssel, schlägt `tsc` fehl (AK-10.5). Texte mit Werten (z. B. «KI-Antwort aus {n} Quellen») sind kleine Funktionen.
- **Kontext:** `LanguageProvider` mit `useT()`; der Umschalter setzt die Sprache, speichert sie unter `localStorage["fdp-lang"]`, setzt `<html lang>` und den Seitentitel (AK-10.2).
- **Startsprache:** gespeicherte Wahl, sonst die erste passende Sprache aus `navigator.languages` (`fr*` → Französisch), sonst Deutsch.
- **Auch übersetzt:** Ratsnamen, Fraktionsnamen, «Bundesrat», «Geschäft», Datumsformat (`Intl.DateTimeFormat` mit `de-CH` bzw. `fr-CH`), Beispielfragen, Hinweise bei fehlender Grundlage, Ladehinweis, Footer.
- **Nicht übersetzt:** der Name «Frag das Parlament» (Logo, offene Frage in der Spec), die Antwort selbst (Sprache der Frage, AK-10.4) und die Textausschnitte der Quellen (Originalsprache).

## 6. Übersetzbare Fehlermeldungen (Backend)

Die API liefert Fehler heute als deutschen Text in `detail`. Damit die UI sie übersetzen kann, setzt `POST /ask` bei jedem Fehler zusätzlich den Header `X-Error-Code` (AK-10.3, AK-14.2):

| Status | Code | Fall |
|---|---|---|
| 429 | `rate_limit` | Rate-Limit pro IP (mit `Retry-After`) |
| 429 | `daily_budget` | Tagesbudget aufgebraucht (mit `Retry-After`) |
| 503 | `llm_unavailable` | LLM nicht konfiguriert oder vorübergehend nicht erreichbar |
| 503 | `unavailable` | Kostenzähler nicht lesbar |
| 422 | `model_refused` | Das Modell hat die Anfrage abgelehnt |

`detail` bleibt unverändert, damit andere Clients nichts merken. Validierungsfehler von FastAPI (422 ohne Code) und Netzwerkfehler erkennt die UI selbst. Unbekannte Codes zeigen eine allgemeine Meldung mit HTTP-Status. nginx reicht den Header unverändert durch.

## 7. Komponenten

```
web/src/
  theme.css            Tokens hell/dunkel, Tailwind-Mapping, Schriften
  theme/               Präferenz, Speicher, Hook useTheme
  i18n/                de.ts, fr.ts, LanguageProvider, useT
  components/
    Header.tsx         Logo, Info-Knopf, Sprach- und Darstellungs-Umschalter
    Notice.tsx         Hinweis «Privates Projekt»
    AskForm.tsx        Suchkarte (bestehend, umgebaut)
    Answer.tsx         Antwort mit Zitat-Marken (bestehend, umgebaut)
    SourceCard.tsx     Quellenkarte (bestehend, umgebaut)
    HowItWorks.tsx     Dialog «So funktioniert's»
    Footer.tsx
  assets/              Logo hell/dunkel (zugeschnitten, optimiert)
public/                Favicon, Apple-Touch-Icon, Web-Manifest
```

- **Dialog «So funktioniert's»:** natives `<dialog>` mit `showModal()`. Das bringt Fokusfalle, Esc und Hintergrund-Sperre mit; beim Schliessen kehrt der Fokus zum Knopf zurück (AK-12.2). Falls jsdom `showModal` nicht kennt, ergänzt das Test-Setup eine kleine Attrappe.
- **Breakpoint:** `sm` (640 px) trennt Handy- und Desktop-Kopfzeile; der Inhalt ist darüber zentriert und auf rund 760 px begrenzt, der Antworttext auf rund 68 Zeichen (AK-11.3).
- **Bewegung:** Übergänge nur für Farben und das Öffnen des Dialogs, abgeschaltet bei `prefers-reduced-motion` (AK-13.3).

## 8. Logo, Icons und Schriften

- **Logo:** Die Originale (1774 × 887 px, JPEG mit Hintergrund) ziehen nach `docs/design/` um. In `web/src/assets/` liegen auf den Inhalt zugeschnittene Fassungen für die Kopfzeile in doppelter Auflösung (WebP, Ausweich-PNG). Erzeugt werden sie einmalig; Werkzeug und Befehl hält Task 7.1 in `docs/design/README.md` fest. Ins Build kommt kein Bildwerkzeug.
- **Icons:** Signet (Bundeshaus mit Sprechblase) als Favicon (32 px), Apple-Touch-Icon (180 px) und Icons im Web-Manifest (192 und 512 px) in `web/public/` (AK-8.3).
- **Schriften:** Inter (Text) und Plus Jakarta Sans (Überschriften) als variable Schriften über `@fontsource-variable`, nur der lateinische Zeichensatz. Vite bündelt sie; der Browser lädt nichts von Dritten (Nicht-Ziel «keine Anfragen an Drittanbieter»). Beide Schriften stehen unter der SIL Open Font License.

## 9. Tests und Messungen

- **Bestehende Web-Tests** bleiben grün; angepasst werden nur Texte und Selektoren (AK-14.1).
- **Neue Tests:**
  - Theme: Präferenz, Speicher, Speicher nicht verfügbar, Wechsel des Systems.
  - Sprache: Startsprache, Umschalten, `<html lang>`, Fehlermeldungen auf Französisch.
  - Dialog: Öffnen, Esc, Fokus zurück.
  - Kontraste der Tokens.
  - axe auf Startseite, Antwort, Fehler und Dialog (AK-13.1), über `axe-core` als Dev-Abhängigkeit. jsdom kann keine Kontraste rechnen; die deckt der Token-Test ab.
- **Backend:** Tests für `X-Error-Code` in jedem Fehlerfall.
- **Lighthouse:** lokal gegen den `web`-Container, mobil, hell und dunkel (Qualitätsziele der Spec). Ergebnis in die PR-Beschreibung von Task 7.7 und ins README; nicht in der CI.
- **Grösse des Builds:** Ausgangswert vor dem Redesign (gemessen in Task 7.1, `vite build`): JavaScript 232.4 kB (gzip 73.2 kB), CSS 15.8 kB (gzip 4.0 kB), zusammen **77.2 kB gzip**. Richtwert: höchstens 20 % mehr, also 92.6 kB gzip (Qualität geht vor, Überschreitung begründen). Schriften und Bilder werden separat gemessen. Nach Task 7.1: JavaScript gzip 73.2 kB, CSS gzip 7.1 kB (die `@font-face`-Regeln aller Zeichensätze), zusammen 80.3 kB (+4 %). Nach Task 7.2: JavaScript gzip 74.4 kB, CSS gzip 7.4 kB, zusammen 81.8 kB (+6 %); dazu die Logo-Dateien (WebP je 6.7 kB). Nach Task 7.3: JavaScript gzip 75.3 kB, CSS gzip 7.4 kB, zusammen 82.7 kB (+7 %); `index.html` mit dem Script gegen Aufblitzen 0.9 kB gzip. Nach Task 7.4: JavaScript gzip 78.0 kB, CSS gzip 7.7 kB, zusammen 85.7 kB (+11 %); der Zuwachs sind vor allem die beiden Wörterbücher. Für Deutsch und Französisch lädt der Browser nur die lateinischen Schriftdateien: Inter 48 kB und Plus Jakarta Sans 27 kB (WOFF2); die übrigen Zeichensätze liegen im Build, werden aber nur bei Bedarf geladen.

## 10. Risiken

| Risiko | Massnahme |
|---|---|
| Französische Texte klingen holprig | Texte kurz halten; Sandro liest die französische Fassung in Task 7.4 gegen |
| Logo als JPEG wird unscharf | Zuschnitt in doppelter Auflösung; SVG-Fassung als offene Frage |
| jsdom kennt `<dialog>` nur teilweise | Attrappe im Test-Setup; echtes Verhalten im Browser prüfen |
| Inline-Script gegen Aufblitzen kollidiert mit einer späteren CSP | Im Plan vermerkt; dann Hash in die CSP |
| Rot und Navy zu ähnlich für Farbfehlsichtige | Zitate unterscheiden sich zusätzlich durch Form (Marke mit Nummer), nicht nur durch Farbe |

## 11. Entscheidungsprotokoll

| Datum | Entscheid | Begründung |
|---|---|---|
| 2026-11-18 | Spec 002 als eigener Ordner; User Stories fortlaufend ab US-8, Tasks als Phase 7 (7.x), damit Bezeichnungen und Branch-Namen eindeutig bleiben. `CLAUDE.md` und `/next-task` lesen die aktive Spec. | Spec 001 ist abgeschlossen und bleibt als Grundlage stehen. |
| 2026-11-18 | Keine Anlehnung an parlament.ch; eigenes Erscheinungsbild aus den Farben des Logos. | Sandro; Nutzungsbedingungen der Parlamentsdienste (kein Eindruck einer amtlichen Veröffentlichung). |
| 2026-11-18 | Entwurf **A «Klar»** gewählt (gegen B «Band» und C «Bulletin»). | Sandro. Ruhig, gut lesbar, auf dem Handy am kompaktesten; Rot nur als Akzent. |
| 2026-11-18 | Übersetzung und Dark Mode als eigener Code (typisierte Wörterbücher, `data-theme`), keine Bibliotheken. | Zwei Sprachen und drei Modi rechtfertigen keine Abhängigkeit; fehlende Übersetzungen fängt der Typ ab. |
| 2026-11-18 | Fehlercodes als Header `X-Error-Code`, `detail` bleibt. | Übersetzbare Meldungen ohne Bruch der API für andere Clients. |
| 2026-11-18 | Task 7.1: Rahmen der Eingabefelder dunkler als im Prototyp (`#7d8ea3` hell, `#66779b` dunkel), weil `#b7c3d2` bzw. `#4a5878` die 3:1 für Bedienelemente verfehlten (Kontrasttest). nginx liefert `manifest.webmanifest` mit eigenem Block als `application/manifest+json` aus, weil `mime.types` die Endung nicht kennt. Logo und Icons erzeugt `docs/design/make-assets.mjs` einmalig mit `sharp`, das nur vorübergehend installiert wird. | Kontrastziel der Spec (AK-9.4, AK-13.4); keine Bildwerkzeuge im Build. |
| 2026-11-18 | Task 7.2: Lesebreite der Antwort `max-w-[62ch]` statt 68ch, gemessen rund 70 Zeichen pro Zeile (68ch ergab 77, AK-11.3 verlangt höchstens rund 75). Beispielfragen am Desktop 36 px hoch, auf Touch-Geräten (`pointer: coarse`) und auf dem Handy 44 px (AK-11.1); Links im Fliesstext des Footers sind nach WCAG 2.5.8 ausgenommen. Die Zeile zu Verbrauch und Kosten bleibt klein unter der Antwort (Spec 001). Geprüft mit Edge headless (playwright-core, nur lokal) bei 360 × 740, 768 und 1440 px, hell und dunkel: kein horizontales Scrollen, Knopf «Fragen» auf dem Handy bei 636 px sichtbar. | Messung statt Schätzung; Klickflächen für Touch, ohne den Desktop aufzublähen. |
| 2026-11-18 | Grössenziel der Spec ist ein Richtwert (höchstens +20 % JavaScript und CSS, gzip); eine Überschreitung aus Qualitätsgründen ist erlaubt und wird hier begründet. | Sandro: «Qualität geht vor», das Ziel aber einigermassen einhalten. |
| 2026-11-18 | Task 7.3: Wahl unter `localStorage["fdp-theme"]` (`system` löscht den Eintrag). Das Script in `index.html` und `src/theme/preference.ts` haben dieselbe Logik; `index.test.ts` führt das Script für alle Kombinationen aus gespeicherter Wahl und System aus und vergleicht. Auch `meta theme-color` folgt der Wahl (bei `system` wieder je Media Query). Die Variante `dark:` hängt an `[data-theme=dark]`; der Media-Query-Block der Tokens bleibt als Ersatz ohne JavaScript. Geprüft mit Edge: gespeichert «dunkel» bei hellem System ist schon ohne React dunkel; die Wahl übersteht das Neuladen; «Wie System» folgt einem Wechsel im Betrieb. | AK-9.1 bis AK-9.3; Sandro wünschte auch die Farbe der Browserleiste. |
| 2026-11-18 | Task 7.4: Wörterbücher `src/i18n/de.ts` und `fr.ts` (Typ `Messages = typeof de`), Sprache unter `localStorage["fdp-lang"]`, sonst die erste deutsche oder französische Sprache aus `navigator.languages`, sonst Deutsch. `format.ts` bekommt Texte und Locale als Parameter (Zahlen `7’818` bzw. `7 818`). `ApiError` trägt eine Art (`network`, `validation`, `http`); die Oberfläche formuliert die Meldung beim Anzeigen, damit sie beim Sprachwechsel mitwechselt. Meldungen mit `detail` der API bleiben bis Task 7.5 deutsch. Beispielfragen tragen ihre Sprache (`lang`-Attribut), ebenso die Zitate der Quellen und die Knöpfe DE/FR (benannt «Deutsch» bzw. «Français»). Französische Typografie: geschütztes Leerzeichen vor «?» und «:». Die französischen Texte liest Sandro im Pull Request gegen. | AK-10.1, AK-10.2, AK-10.4, AK-10.5; Barrierefreiheit (Aussprache durch Screenreader). |
