# Tasks 003 – Person und Zeitraum aus der Frage

Immer nur einen Task gleichzeitig bearbeiten. Ein Task ist erst erledigt, wenn die Definition of Done in `CLAUDE.md` erfüllt ist. Der nächste Task beginnt erst, wenn der Pull Request des vorherigen gemergt ist. Die Nummerierung setzt Spec 002 fort (Phase 8); Branches heissen `task/8.x-<kurzname>`.

## Phase 8 – Person und Zeitraum

- [x] 8.0 Spec, Plan und Tasks; `CLAUDE.md` nennt Spec 003 als aktive Spec
- [x] 8.1 Goldset v3 und Baseline: neue Tags `person-zeit` und `ausserhalb` (Schema, README des Goldsets), mindestens 10 Fragen mit Person und/oder Zeitraum und mindestens 3 Fragen ausserhalb des Datenbestands, von Claude vorgeschlagen und von Sandro geprüft; Baseline-Lauf (Retrieval `full`, Antworten auf den neuen Teilsets) vor jeder Codeänderung (AK-19.1, AK-19.2)
- [x] 8.2 Filter «Person» im Backend: `speaker` in `SearchFilters` und SQL (Geschäfte fallen weg), `--speaker` in `search` und `ask`, `GET /speakers`; Vektorsuche mit Personenfilter messen, bei Bedarf exakte Suche (AK-18.2, AK-18.3)
- [x] 8.3 Erkennung: Paket `query/` mit Katalog aus der Datenbank (Zeitraum, Sessionen, Personen), Erkennung von Zeitangaben und Personen DE/FR nach den Regeln im Plan, Mehrdeutigkeit, Titelregel; Unit-Tests mit Beispielsätzen ohne Datenbank, Latenz gemessen (AK-17.1, AK-17.3, AK-17.6)
- [ ] 8.4 Pipeline und API: Erkennung anwenden, Vorrang gesetzter Filter, Datenbestand (`out_of_range` ohne Suche und LLM, teilweise Überlappung), Fallback ohne Person, neue Felder in `POST /ask`, Schalter `QUERY_DETECTION` und `detect`, Ausgabe in der CLI; Eval-Runner mit Erkennung, Vergleich mit der Baseline, Entscheid zum Entfernen von Namen und Jahren aus dem Suchtext; Smoke-Eval (AK-16.1 bis AK-16.3, AK-17.2, AK-17.4, AK-17.5, AK-19.2, AK-19.3)
- [ ] 8.5 Web-UI: Zeile mit erkannten Filtern zum Entfernen, Hinweis ausserhalb des Datenbestands und bei teilweiser Überlappung, Auswahl bei mehrdeutigem Namen, Hinweis nach Suche ohne Person, Feld «Person» als Combobox mit Vorschlägen; Deutsch und Französisch, axe, Edge-Prüfung bei 360, 768 und 1440 px, Screenshots früh zeigen (AK-16.4, AK-17.3, AK-17.5, AK-18.1)
- [ ] 8.6 Abschluss: Eval `full` mit und ohne Erkennung, Ergebnisse im README, README-Abschnitte (Filter, API, Web-UI), Screenshots, Spec 003 als umgesetzt markieren, Demo auf dem Server aktualisieren (Sandro mit Anleitung)
