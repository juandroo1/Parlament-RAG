# Spec 002 – Redesign der Web-UI

Status: Umgesetzt · Version 1.1 (Ergänzung Filter, Task 7.9)

Baut auf [Spec 001](../001-frag-das-parlament/spec.md) auf. Architektur, Daten, Leitplanken und alle Akzeptanzkriterien von Spec 001 gelten weiter; diese Spec ändert nur die Web-UI. User Stories und Akzeptanzkriterien sind fortlaufend nummeriert (ab US-8), damit die Bezeichnungen im ganzen Projekt eindeutig bleiben.

## 1. Problem

Die Web-UI aus Spec 001 (Task 5.2) funktioniert, wirkt aber schlicht: ohne Logo, ohne eigene Farbwelt, nur auf Deutsch, und sie erklärt nicht, was hinter den Antworten steckt. Wer über einen Link auf die öffentliche Demo kommt, versteht nicht sofort, was die Seite kann, wie weit man ihr trauen darf und dass sie kein Angebot des Parlaments ist. Auf dem Handy brauchen die Beispielfragen und Filter viel Platz.

## 2. Ziel

Eine ansprechende, eigenständige und vertrauenswürdige Oberfläche:

- mit dem eigenen Logo und einer Farbwelt aus dem Logo;
- mit hellem und dunklem Modus;
- auf Deutsch und Französisch umschaltbar;
- auf dem Handy und am Desktop gut bedienbar;
- mit einem kurzen Bereich «So funktioniert's», der Datenquelle, Vorgehen und Grenzen erklärt.

Die Funktionen bleiben gleich: Frage stellen, Antwort mit klickbaren Zitaten, Quellen, Filter, Hinweis bei fehlender Grundlage.

## 3. Zielgruppe

- Interessierte Bürgerinnen und Bürger aus der Deutsch- und der Westschweiz, oft auf dem Handy.
- Persona: Nathalie, 52, Lehrerin in Freiburg, zweisprachig. Sie hört in den Nachrichten von einer Debatte im Ständerat und will unterwegs auf dem Handy nachsehen, was dazu gesagt wurde, und die Originalstelle öffnen.

## 4. Designgrundlage

- **Logo:** `web/src/assets/frag-das-parlament-logo.jpeg` (hell) und `web/src/assets/frag-das-parlament-logo-dark.jpeg` (dunkel), je 1774 × 887 px: Silhouette des Bundeshauses, Sprechblase mit Schweizerkreuz und der Schriftzug «Frag das Parlament».
- **Farben aus dem Logo** (gemessen, Feinwerte im Plan):

  | Rolle | Hell | Dunkel |
  |---|---|---|
  | Hintergrund | Weiss `#ffffff` | Nachtblau `#121622` |
  | Text, Primärfarbe | Navy `#0f243f` | Off-White `#f4f5f7` |
  | Akzent (sparsam) | Rot `#da2727` | Rot `#e00d0f` |

  Grautöne, Flächen und Zustände werden daraus abgeleitet und als Design-Tokens an einer Stelle definiert.
- **Eigenständig, nicht amtlich:** Die Nutzungsbedingungen der Parlamentsdienste verlangen, dass die Nutzung nicht den Eindruck einer amtlichen Veröffentlichung erweckt. Die UI ahmt deshalb keine Behördenseite nach. Das Logo verwendet das Schweizerkreuz dekorativ zusammen mit Sprechblase und eigenem Namen, nicht das Wappen der Eidgenossenschaft.
- **Vorgehen:** Vor `plan.md` und `tasks.md` entstanden drei Designentwürfe als klickbarer Prototyp (A «Klar», B «Band», C «Bulletin»). Gewählt ist A; Beschreibung in [plan.md](plan.md), Abschnitt 2.

## 5. User Stories und Akzeptanzkriterien

### US-8 Erscheinungsbild
Als Nutzerin will ich auf den ersten Blick sehen, was die Seite ist und von wem sie stammt.

- AK-8.1: Die Kopfzeile zeigt das Logo, im dunklen Modus die dunkle Variante. Die Farben stammen aus der Palette in Abschnitt 4 und sind als Design-Tokens an einer Stelle definiert.
- AK-8.2: Die UI ahmt keine Behördenseite nach: kein Wappen der Eidgenossenschaft, keine Schrift und kein Layout von parlament.ch oder admin.ch, kein Schriftzug «Das Schweizer Parlament». Der Hinweis «Privates Projekt, keine amtliche Veröffentlichung» ist auf der Startseite ohne Scrollen sichtbar, auf dem Handy und am Desktop.
- AK-8.3: Favicon und App-Icon (Homescreen) zeigen das Signet aus dem Logo.
- AK-8.4: Quelle, Stand und Datum des Downloads, der Hinweis auf die KI-Antwort und die Lizenz bleiben im Footer (Nutzungsbedingungen, Task 6.3a).

### US-9 Dunkler Modus
Als Nutzerin will ich die Seite hell oder dunkel nutzen.

- AK-9.1: Ohne eigene Wahl folgt die Seite der Einstellung des Systems (`prefers-color-scheme`).
- AK-9.2: Ein Umschalter in der Kopfzeile bietet Hell, Dunkel und System. Die Wahl bleibt nach dem Neuladen erhalten. Ist kein Speicher verfügbar (privates Fenster), funktioniert die Seite trotzdem.
- AK-9.3: Beim Laden blitzt der falsche Modus nicht auf.
- AK-9.4: Beide Modi erfüllen die Kontrastanforderungen von WCAG 2.2 AA.

### US-10 Sprache der Oberfläche
Als Nutzerin aus der Westschweiz will ich die Oberfläche auf Französisch.

- AK-10.1: Ein Umschalter DE/FR in der Kopfzeile wechselt alle Texte der Oberfläche: Kopfzeile, Formular, Beispielfragen, Filter, Ladehinweis, Antwort- und Quellenbereich, Fehlermeldungen, «So funktioniert's» und Footer.
- AK-10.2: Die Startsprache ist die gespeicherte Wahl, sonst die Sprache des Browsers (Französisch für `fr*`, sonst Deutsch). `<html lang>` und Seitentitel passen zur Sprache.
- AK-10.3: Meldungen der API (Rate-Limit, Tagesbudget, Fehler) erscheinen in der gewählten Sprache.
- AK-10.4: Die Sprache der Antwort folgt weiterhin der Frage (AK-1.1), nicht der Oberfläche.
- AK-10.5: Fehlt eine Übersetzung, schlägt die Typprüfung oder ein Test fehl.

### US-11 Handy und Desktop
Als Nutzerin will ich die Seite auf dem Handy genauso gut nutzen wie am Desktop.

- AK-11.1: Von 360 px bis 1440 px Breite gibt es kein horizontales Scrollen. Bedienelemente sind auf Touch-Geräten mindestens 44 × 44 px gross.
- AK-11.2: Auf dem Handy (360 × 740 px) sind Fragefeld und Knopf «Fragen» ohne Scrollen sichtbar.
- AK-11.3: Der Antworttext hat eine gut lesbare Zeilenlänge (höchstens rund 75 Zeichen). Am Desktop nutzt das Layout die Breite sinnvoll; die genaue Anordnung legt der gewählte Entwurf fest.

### US-12 So funktioniert's
Als Nutzerin will ich kurz verstehen, woher die Antworten kommen und wie weit ich ihnen trauen kann.

- AK-12.1: Ein kleiner Knopf öffnet einen kurzen Bereich mit:
  - was die Seite macht;
  - woher die Daten stammen und mit welchem Stand;
  - wie eine Antwort entsteht (Suche in den Protokollen, KI-Antwort nur aus den gefundenen Stellen, jede Aussage mit Quelle);
  - Grenzen (die KI kann sich irren, massgebend ist die Originalstelle, keine Wertungen);
  - Datenschutz (Fragen werden nicht gespeichert) und das Tageslimit der Demo;
  - Link zum Code und zu den Eval-Ergebnissen.
- AK-12.2: Der Bereich ist per Tastatur bedienbar, schliesst mit Esc und gibt den Fokus an den Knopf zurück.
- AK-12.3: Der Inhalt liegt auf Deutsch und Französisch vor.

### US-13 Barrierefreiheit
Als Nutzerin mit Screenreader oder ohne Maus will ich die Seite vollständig bedienen können.

- AK-13.1: Automatische Prüfung mit axe in den Web-Tests ohne Verstösse: Startseite, Antwort, Fehler und «So funktioniert's».
- AK-13.2: Alle Funktionen sind per Tastatur erreichbar, der Fokus ist sichtbar.
- AK-13.3: Animationen respektieren `prefers-reduced-motion`.
- AK-13.4: Die Kontraste der Farb-Tokens werden in einem Test berechnet: mindestens 4.5:1 für Text und 3:1 für Bedienelemente, in beiden Modi.

### US-14 Bestehende Funktionen
Als Nutzerin will ich alles weiterhin tun können, was die bisherige Oberfläche konnte.

- AK-14.1: Frage stellen, Beispielfragen, Filter (Rat, Fraktion, Zeitraum), klickbare Zitate, Quellen mit Metadaten und Link (AK-2.1, AK-2.2), Hinweis bei fehlender Grundlage (AK-3.1), Lade- und Fehlerzustand funktionieren wie bisher. Die bestehenden Web-Tests bleiben grün; angepasst werden nur Texte und Selektoren.
- AK-14.2: Das Backend ändert sich nur, soweit AK-10.3 es verlangt.

### US-15 Filter (Ergänzung, Version 1.1)
Als Nutzerin will ich die Filter bei Bedarf schnell aufklappen, ohne dass sie sonst Platz brauchen.

- AK-15.1: Der Knopf «Filter» bleibt wie in Variante A neben dem Knopf «Fragen» und nennt die Zahl der aktiven Filter. Neu zeigt er einen Pfeil, der beim Öffnen dreht. Auf Touch-Geräten ist er mindestens 44 × 44 px gross (AK-11.1).
- AK-15.2: Der Filterbereich klappt mit einer kurzen Animation auf und zu; bei `prefers-reduced-motion` ohne Animation (AK-13.3). Zugeklappt ist er für Tastatur und Screenreader nicht erreichbar; `aria-expanded` und `aria-controls` bleiben.
- AK-15.3: Der Filterbereich klappt unterhalb der Zeile mit «Filter» und «Fragen» auf. Die Anordnung der Felder bleibt wie in Variante A: am Desktop zwei pro Zeile, auf dem Handy untereinander. Mit aktiven Filtern bleiben «Filter» und «Fragen» ab 360 px einzeilig nebeneinander. Kein horizontales Scrollen von 360 px bis 1440 px.
- AK-15.4: Die Filter wirken wie bisher (AK-14.1); axe meldet keine Verstösse, auch mit offenen Filtern (AK-13.1).

## 6. Qualitätsziele

| Metrik | Beschreibung | Ziel |
|---|---|---|
| Lighthouse Performance | Mobil, Produktions-Build | ≥ 90 |
| Lighthouse Accessibility | Mobil, hell und dunkel | ≥ 95 |
| Lighthouse Best Practices | Mobil | ≥ 95 |
| axe | Verstösse in den Web-Tests | 0 |
| Kontrast | Farb-Tokens, beide Modi | WCAG 2.2 AA |
| Grösse | JavaScript und CSS des Builds (gzip) | gemessen; Richtwert höchstens 20 % mehr als vor dem Redesign. Qualität geht vor: Eine Überschreitung ist erlaubt, wird aber begründet (plan.md, Entscheidungsprotokoll) |
| Logo | Ausgelieferte Grösse der Logodateien | optimiert (WebP/PNG statt JPEG in Originalgrösse), gemessen |

## 7. Nicht-Ziele

- Keine Änderungen an Retrieval, Prompts, Datenmodell oder Evals.
- Keine Benutzerkonten, kein gespeicherter Verlauf.
- Kein Italienisch und kein Rätoromanisch in dieser Spec.
- Kein Nachbau des Erscheinungsbilds von parlament.ch oder admin.ch.
- Keine Anfragen an Drittanbieter aus dem Browser: Schriften werden selbst ausgeliefert, kein Tracking und keine Analytics.
- Keine weiteren Seiten oder Routen ausser dem Bereich «So funktioniert's».

## 8. Offene Fragen

- Französische Variante des Logos («Frag das Parlament» bleibt vorerst der Name in beiden Sprachen; die Unterzeile wird übersetzt)?
- Logo als Vektorgrafik (SVG): Die JPEG-Dateien enthalten den Hintergrund und den Schriftzug als Pixel. Eine SVG-Fassung wäre schärfer und kleiner.
- Frage als Link teilen (URL mit Frage und Filtern)?
- Italienische Oberfläche in einer späteren Spec?
- Progressive Web App mit Service Worker: geprüft und vorerst verworfen (plan.md, Entscheidungsprotokoll). Das Manifest macht die Seite schon installierbar; denkbar bleibt ein «maskable» Icon.
