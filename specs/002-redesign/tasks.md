# Tasks 002 – Redesign der Web-UI

Immer nur einen Task gleichzeitig bearbeiten. Ein Task ist erst erledigt, wenn die Definition of Done in `CLAUDE.md` erfüllt ist. Der nächste Task beginnt erst, wenn der Pull Request des vorherigen gemergt ist. Die Nummerierung setzt Spec 001 fort (Phase 7); Branches heissen `task/7.x-<kurzname>`.

## Phase 7 – Redesign

- [x] 7.0 Spec, Plan und Tasks für das Redesign; drei Designentwürfe als Prototyp, Entscheid für Variante A; `CLAUDE.md` und `/next-task` lesen die aktive Spec
- [x] 7.1 Grundlagen: Design-Tokens hell und dunkel in `theme.css` mit Tailwind-Mapping, Tokens für «keine Grundlage» und Fehler, Kontrasttest der Tokens; Schriften selbst gehostet (Inter, Plus Jakarta Sans); Logo zugeschnitten und optimiert (Originale nach `docs/design/`, Vorgehen in `docs/design/README.md`); Favicon, Apple-Touch-Icon und Web-Manifest; gzip-Grösse des Builds als Ausgangswert messen (AK-8.3, AK-9.4, AK-13.4)
- [x] 7.2 Layout nach Variante A: Kopfzeile mit Logo, Hinweis «Privates Projekt», Einstieg mit Suchkarte, Antwort mit Zitat-Marken, Quellenkarten, Footer; Handy und Desktop; vorerst nur Deutsch und Dark Mode nach System (AK-8.1, AK-8.2, AK-8.4, AK-11.1 bis AK-11.3, AK-14.1)
- [x] 7.3 Dark Mode: Präferenz System/Hell/Dunkel mit Speicher, Script gegen Aufblitzen, Umschalter in der Kopfzeile (Desktop drei Knöpfe, Handy ein Knopf), Logo je Modus (AK-9.1 bis AK-9.3)
- [x] 7.4 Französisch: i18n-Modul mit typisierten Wörterbüchern, alle Texte der Oberfläche inklusive Rat, Fraktion und Datum, Startsprache aus Speicher oder Browser, `<html lang>` und Titel, Umschalter DE/FR; Sandro liest die französischen Texte gegen (AK-10.1, AK-10.2, AK-10.4, AK-10.5)
- [ ] 7.5 Übersetzbare Fehlermeldungen: Header `X-Error-Code` in `POST /ask` (Backend und Tests), Zuordnung in der UI inklusive Wartezeit aus `Retry-After`, auf Deutsch und Französisch (AK-10.3, AK-14.2)
- [ ] 7.6 «So funktioniert's»: Knopf in der Kopfzeile, Dialog als Seitenleiste (Desktop) bzw. Blatt von unten (Handy), Inhalte auf Deutsch und Französisch, Links zu Code und Eval-Ergebnissen (AK-12.1 bis AK-12.3)
- [ ] 7.7 Barrierefreiheit und Qualität: axe-Tests für Startseite, Antwort, Fehler und Dialog, Tastaturbedienung, `prefers-reduced-motion`; Lighthouse mobil hell und dunkel, Grösse des Builds gegen den Ausgangswert (AK-13.1 bis AK-13.3, Qualitätsziele)
- [ ] 7.8 Abschluss: neue Screenshots (hell, dunkel, Handy) im README, README-Abschnitte zur Web-UI nachführen, offene Fragen der Spec aktualisieren, Demo auf dem Server aktualisieren (Sandro mit Anleitung)
