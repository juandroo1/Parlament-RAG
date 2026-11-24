# Plan 003 – Person und Zeitraum aus der Frage

Status: Freigegeben · Version 1.0 · gehört zu [spec.md](spec.md)

## 1. Grundsatz

- Die Erkennung ist ein eigenes, reines Modul ohne Datenbank und ohne Netz: Frage und Katalog rein, erkannte Filter raus. So lässt sie sich mit vielen Beispielsätzen testen (AK-17.6).
- Der Katalog (Personen, Sessionen, abgedeckter Zeitraum) kommt aus der Datenbank. Kein neues Schema, keine neue Tabelle: Alles lässt sich aus `documents` ableiten. Damit braucht der Server keine Migration und keinen neuen Datentransfer.
- Erkannte Filter laufen durch denselben Weg wie gesetzte Filter (`SearchFilters`, SQL vor der Suche, AK-4.1). Suche, `ask`, API und Evals nutzen dieselbe Pipeline (Spec 001, plan.md Abschnitt 1).
- Lieber nicht filtern als falsch filtern: Im Zweifel (mehrdeutiger Name, Jahreszahl als Teil eines Titels) bleibt die Frage ohne Filter.

## 2. Ablauf einer Frage

```
Frage + gesetzte Filter
  → Erkennung (Zeitraum, Person) gegen den Katalog         nur wenn eingeschaltet
  → Filter zusammenführen: gesetzte Filter haben Vorrang   AK-17.2
  → Datenbestand prüfen: Zeitraum ganz ausserhalb?         ja → Hinweis `out_of_range`, Ende (AK-16.1)
  → Suche mit den Filtern
  → nur erkannter Personenfilter und zu wenig Treffer?     ja → Suche ohne Person wiederholen (AK-17.4)
  → Antwort wie bisher (Schwelle, LLM, Zitate)
  → Antwort + angewandte Filter + Hinweise                 AK-16.2, AK-17.5
```

## 3. Katalog

Neues Paket `src/parlrag/query/` mit `catalog.py`, `time.py`, `person.py`, `detect.py`.

`Catalog` wird aus der Datenbank geladen (`load_catalog(connection)`) oder in Tests direkt gebaut:

| Teil | Quelle | Inhalt |
|---|---|---|
| Zeitraum | `min(date)`, `max(date)` der Voten (`source_type = 'transcript'`) | erstes und letztes Datum (AK-16.3) |
| Sessionen | Voten gruppiert nach `session_id`: erstes und letztes Datum | Art und Jahr aus dem Monat der Mitte: 2–3 Frühjahrssession, 4–5 Sondersession, 6 Sommersession, 9–10 Herbstsession, 11–12 Wintersession. Stand heute 15 Sessionen (5201 bis 5215) |
| Personen | `speaker_name` der Voten mit der jüngsten Fraktion, Kanton, Rat und Funktion sowie der Zahl der Voten | 276 Personen. `speaker_name` ist «Nachname Vorname» (z. B. «Michaud Gigon Sophie», «Büchel Roland Rino»); ein getrennter Vor- und Nachname ist nicht gespeichert |

- Die API lädt den Katalog beim Start und danach höchstens alle 10 Minuten neu (ein neuer Ingest ist so ohne Neustart sichtbar). Die CLI lädt ihn pro Aufruf.
- Die Abfragen nutzen den bestehenden Index auf `(date, council, parl_group)` bzw. einen Scan der rund 26 000 Voten; gemessen in Task 8.3, Ziel unter 200 ms beim Laden.

## 4. Zeitraum erkennen

Regeln über Muster, Deutsch und Französisch. Eine Jahreszahl allein ist kein Zeitraum; sie braucht ein Signalwort, damit «Energiestrategie 2050» oder «Agenda 2030» nicht zum Filter werden.

| Muster (Beispiele) | Zeitraum |
|---|---|
| «im Jahr 2025», «2025» nach «im», «in», «während», «en», «durant», «pendant», «au cours de» | 1.1. bis 31.12. |
| «im März 2025», «en mars 2025» | ganzer Monat |
| «Herbstsession 2025», «in der Sommersession 2024», «session d’automne 2025», «session d’été 2024», «Sondersession 2025», «session spéciale 2025» | erstes bis letztes Datum dieser Session aus dem Katalog. Gibt es die Session im Katalog nicht (z. B. «Herbstsession 2022»), gilt das Kalenderfenster der Session (Herbst: September), damit AK-16.1 greift |
| «seit 2024», «ab 2024», «depuis 2024», «à partir de 2024» | ab 1.1., offenes Ende |
| «vor 2025», «bis 2024», «avant 2025», «jusqu’en 2024» | offenes Ende vorne, bis 31.12. des Vorjahres bzw. des Jahres |
| «zwischen 2024 und 2025», «von 2024 bis 2025», «entre 2024 et 2025», «de 2024 à 2025» | 1.1. des ersten bis 31.12. des zweiten Jahres |
| «in der letzten Session», «lors de la dernière session» | letzte Session im Katalog |

- Jahre nach dem laufenden Jahr werden nicht als Zeitraum erkannt («bis 2050 klimaneutral» ist ein Ziel, kein Zeitraum).
- Relative Angaben wie «letztes Jahr» oder «vor zwei Wochen» werden nicht erkannt (Nicht-Ziel; zu fehleranfällig gegenüber dem Stand der Daten).
- Mehrere Angaben in einer Frage: Die erste erkannte gilt, die anderen werden ignoriert. Widersprüchliche Angaben («seit 2025 bis 2024») ergeben keinen Filter.

## 5. Person erkennen

Abgleich der Frage mit den Personen im Katalog über Wörter (Tokens), gross- und kleinschreibungsunabhängig, Akzente normalisiert («Celine» findet «Céline»).

- **Treffer:** Eine Folge von Wörtern in der Frage, die alle im Namen einer Person vorkommen, mindestens eines davon nicht das letzte Wort des Namens (das ist in der Regel der Vorname). «Funiciello», «Tamara Funiciello», «Funiciello Tamara» und «Michaud Gigon» treffen; «Tamara» allein trifft nicht.
- **Funktion:** «Bundesrat Rösti», «Bundesrätin Baume-Schneider», «Nationalrätin Funiciello», «Ständerat Würth», «conseiller fédéral Rösti», «conseillère nationale Funiciello», «Bundespräsidentin …» werden als Hinweis auf eine Person gelesen. «Bundesrat» oder «Conseil fédéral» allein meint das Gremium, nicht eine Person: kein Filter.
- **Nur der Nachname:** Zählt nur, wenn er eindeutig ist und neben einem Signal steht: Funktion, Vorname oder ein Verb des Sagens bzw. eine Zuschreibung («sagte», «hat … gesagt», «meinte», «betonte», «laut», «gemäss», «von», «a dit», «selon», «d’après», «de»). So wird «Fischer» in «Was sagte der Rat zu den Fischern?» nicht zur Person.
- **Mehrdeutig:** Passt ein Treffer auf mehrere Personen (z. B. «Müller» auf Damian Müller und Leo Müller, «Graf» auf Maya Graf und Priska Seiler Graf), wird nicht gefiltert. Die Antwort enthält die möglichen Personen (`speaker_candidates`, AK-17.3).
- **Titel:** «Initiative Funiciello», «Motion Funiciello», «initiative parlementaire Funiciello» werden erkannt, gelten aber als Hinweis auf ein Geschäft, nicht auf die Rednerin: kein Personenfilter. Der Fallback in Abschnitt 7 fängt weitere Fälle ab.
- Personen ohne Voten im Korpus (z. B. ehemalige Ratsmitglieder) sind nicht im Katalog und werden nicht erkannt (Offene Fragen der Spec).

## 6. Filter «Person» (`speaker`)

- `SearchFilters` bekommt `speaker: str | None` mit dem Wert von `speaker_name` («Funiciello Tamara»). Kein neuer Schlüssel nötig; Namen sind im Korpus eindeutig (geprüft in Task 8.2).
- SQL in `FILTER_SQL`: `CAST(:speaker AS text) IS NULL OR (d.source_type = 'transcript' AND d.speaker_name = CAST(:speaker AS text))`. Geschäftstexte fallen weg (AK-18.2), wie beim Fraktionsfilter.
- Eine Person hat einige hundert Chunks. Die Vektorsuche mit `iterative_scan = relaxed_order` (Task 2.4) findet sie, muss dafür aber weit scannen. In Task 8.2 messen; ist sie zu langsam oder liefert sie zu wenig Treffer, wird mit Personenfilter exakt gesucht (ohne HNSW-Index, bei wenigen hundert Chunks schnell).
- CLI: `parlrag search|ask --speaker "Funiciello Tamara"`.
- API: `filters.speaker` in `POST /ask`; neu `GET /speakers` mit Name, Fraktion, Kanton, Rat, Funktion (Bundesrat) und Zahl der Voten für die Vorschläge in der UI (AK-18.1). Antwort mit `Cache-Control: max-age=600`.

## 7. Pipeline

`AskPipeline.ask(question, filters, *, detect=True)`:

1. **Erkennen** mit dem Katalog, falls `detect` und die Einstellung `QUERY_DETECTION` (Standard `true`, AK-19.3) es erlauben.
2. **Zusammenführen:** Gesetzte Filter haben Vorrang. Setzt die Nutzerin einen Zeitraum, wird kein Zeitraum aus der Frage übernommen; dasselbe für die Person. Die Antwort merkt sich, welche Filter erkannt wurden.
3. **Datenbestand:** Liegt `[date_from, date_to]` ganz ausserhalb von `[erstes Datum, letztes Datum]`, endet die Pipeline mit `insufficient_reason = "out_of_range"`, ohne Suche und ohne LLM-Aufruf (AK-16.1). Bei teilweiser Überlappung läuft die Suche, die Antwort trägt `coverage.partial = true` (AK-16.2). Das gilt auch für gesetzte Filter (heute endet ein Zeitraum ausserhalb mit `no_hits`).
4. **Suchen** wie bisher.
5. **Fallback** (AK-17.4): Wurde die Person nur erkannt (nicht gesetzt) und liefert die Suche keine Treffer oder liegt die beste Similarity unter `ANSWER_MIN_SIMILARITY`, wird ohne Personenfilter noch einmal gesucht. Die Antwort meldet `retried_without = ["speaker"]`. Beim Zeitraum gibt es keinen Fallback: Ein ausdrücklich genanntes Jahr soll nicht stillschweigend aufgehoben werden.
6. **Antwort** wie bisher (Schwelle, LLM, Zitatprüfung).

Offen für eine Messung in Task 8.4: Erkannte Namen und Zeitangaben aus dem Suchtext entfernen, bevor er eingebettet wird? «Was sagte Funiciello 2025 zur Gleichstellung?» würde dann als «Was sagte zur Gleichstellung?» gesucht. Das kann die Ähnlichkeit zum Thema erhöhen, aber auch Voten verlieren, die den Namen nennen. Entschieden wird per Eval auf `person-zeit`.

## 8. API

`POST /ask`, Anfrage (neu: `speaker`, `detect`):

```json
{"question": "Was sagte Tamara Funiciello 2025 zur Gleichstellung?",
 "filters": {"council": "NR"}, "detect": true}
```

Antwort (neu: `filters`, `coverage`, `speaker_candidates`, `retried_without`; neuer Grund `out_of_range`):

```json
{"answer": "…", "insufficient_context": false, "insufficient_reason": null, "sources": [],
 "usage": {},
 "filters": {"applied": {"council": "NR", "speaker": "Funiciello Tamara",
                         "date_from": "2025-01-01", "date_to": "2025-12-31"},
             "detected": ["speaker", "date_from", "date_to"]},
 "coverage": {"first": "2023-12-04", "last": "2026-10-02", "partial": false},
 "speaker_candidates": [],
 "retried_without": []}
```

- `speaker_candidates`: bei einem mehrdeutigen Namen die möglichen Personen (Name, Fraktion, Kanton), sonst leer.
- `GET /speakers` siehe Abschnitt 6.
- Bestehende Clients bleiben gültig: alle neuen Felder sind optional bzw. kommen nur dazu.

## 9. Web-UI

Baut auf Variante A auf (Spec 002); Screenshots früh zeigen.

- **Erkannte Filter** als kleine Zeile über der Antwort: «Gesucht in: Voten von Tamara Funiciello (SP, BE) · 2025». Jeder erkannte Filter hat einen Knopf zum Entfernen; das fragt erneut mit `detect: false` und den übrigen Filtern als gesetzte Filter (AK-17.5).
- **Ausserhalb des Datenbestands:** eigener Hinweis statt «Keine ausreichende Grundlage»: «Zu diesem Zeitraum gibt es keine Daten. Die Voten reichen vom 4. Dezember 2023 bis 2. Oktober 2026.» Bei teilweiser Überlappung ein Satz unter der Antwort (AK-16.1, AK-16.2).
- **Mehrdeutiger Name:** «Meinten Sie: Damian Müller (RL, LU) · Leo Müller (M-E, LU)?» als Knöpfe; ein Klick fragt erneut mit dieser Person als Filter.
- **Wiederholt ohne Person:** Satz unter der Antwort: «Zu Tamara Funiciello gab es dazu keine passenden Voten; gezeigt werden Voten aller Personen.»
- **Feld «Person»** in den Filtern: Eingabefeld mit Vorschlagsliste nach dem ARIA-Muster «Combobox» (Pfeiltasten, Enter, Esc), Daten aus `GET /speakers`, einmal pro Sitzung geladen. Ohne Bibliothek, wie Spec 002.
- Alle Texte in `de.ts` und `fr.ts`; Datum je Sprache; axe-Tests für die neuen Zustände; Grösse des Builds messen.

## 10. Evals

- **Neue Tags** `person-zeit` und `ausserhalb` im Goldset (`Tag` in `evals/dataset.py`, `evals/datasets/README.md`). Fragen `ausserhalb` sind unbeantwortbar (`answerable: false`); für sie wird zusätzlich der Grund `out_of_range` und «kein LLM-Aufruf» geprüft.
- **Goldset v3:** mindestens 10 Fragen `person-zeit` (Deutsch und Französisch, Person allein, Zeitraum allein, beides; mindestens eine mit mehrdeutigem Namen und eine mit «Initiative X») und mindestens 3 Fragen `ausserhalb`. Die Smoke-Suite bleibt unverändert.
- **Baseline** vor jeder Codeänderung (Task 8.1): Retrieval `full` und Antworten auf den neuen Teilsets, mit dem heutigen Stand.
- **Vergleich** in Task 8.4: derselbe Lauf mit `QUERY_DETECTION=true` und `false`. Der Eval-Runner nutzt dieselbe Erkennung wie die Pipeline (auch für Retrieval-Evals), sonst misst er etwas anderes als die Demo.
- Bestehende Fragen nennen oft «Bundesrat Rösti»; die Erkennung setzt dort neu einen Personenfilter. Wirkung pro Teilset ausweisen, Verschlechterungen einzeln ansehen.
- Evals laufen wie bisher lokal über das Claude-Abo (Haiku), ohne API-Kosten.

## 11. Tests

- `query/time.py` und `query/person.py`: Tabellen mit Beispielsätzen DE/FR (Treffer, Nicht-Treffer wie «Energiestrategie 2050», «die Fischer», «Initiative Funiciello», mehrdeutige Namen, Akzente), mit einem Katalog aus Testdaten (AK-17.6).
- Pipeline: Vorrang gesetzter Filter, `out_of_range` ohne Suche und ohne LLM-Aufruf (Mocks zählen Aufrufe), teilweise Überlappung, Fallback ohne Person, Schalter aus.
- DB-Tests: Filter `speaker` (nur Voten dieser Person, keine Geschäfte), Katalog aus der Datenbank (Zeitraum, Sessionen, Personen).
- API: neue Felder, `GET /speakers`, alte Anfragen ohne neue Felder.
- Web: Zeile mit erkannten Filtern, Entfernen fragt erneut ohne Erkennung, Hinweise, Auswahl bei Mehrdeutigkeit, Combobox per Tastatur, axe.
- Latenz der Erkennung als Test mit grosszügiger Grenze (z. B. 100 Fragen unter 1 s) und Messung im Eval-Lauf.

## 12. Risiken

| Risiko | Gegenmassnahme |
|---|---|
| Falscher Personenfilter (Nachname ist ein Wort, Name im Titel eines Geschäfts) | Signalwörter, Titelregel, Fallback ohne Person, Evals |
| Jahreszahl ist Teil eines Titels oder Ziels | Signalwort nötig, keine Jahre nach dem laufenden Jahr |
| Personenfilter macht die Vektorsuche langsam oder lückenhaft | messen (Task 8.2), sonst exakte Suche bei Personenfilter |
| Frage nennt nur Person und Zeit, aber kein Thema («Was sagte X 2025?») | Similarity bleibt tief, Ablehnung `low_similarity`. Nicht Teil dieser Spec; als Idee in den Offenen Fragen (Themen der Person auflisten) |
| Bestehende Evals ändern sich durch erkannte Personen | pro Teilset vergleichen; Schalter für Läufe ohne Erkennung |
| Katalog veraltet nach Ingest | Neuladen alle 10 Minuten in der API |

## 13. Entscheidungsprotokoll

| Datum | Entscheid | Begründung |
|---|---|---|
| 2026-11-24 | Spec 003 als eigener Ordner; User Stories ab US-16, Tasks als Phase 8 (8.x). | Fortlaufende Nummern wie in Spec 002. |
| 2026-11-24 | Erkennung über Regeln (Katalog aus der Datenbank, Muster für Zeitangaben), **kein zusätzlicher LLM-Aufruf**. | Sandro. Gratis, schnell, deterministisch und gut testbar; ein LLM-Aufruf würde jede Frage verteuern und um 1 bis 2 s verlangsamen. |
| 2026-11-24 | Erkannte Filter werden **automatisch angewandt** und sichtbar angezeigt, mit Möglichkeit zum Entfernen. | Sandro. Sonst müsste man zweimal fragen. |
| 2026-11-24 | Kein neues Schema: Personen, Sessionen und Zeitraum werden aus `documents` abgeleitet, Personenfilter über `speaker_name`. | Keine Migration und kein neuer Datentransfer auf den Server; Vor- und Nachname getrennt zu speichern bräuchte einen neuen Ingest. |
| 2026-11-24 | Task 8.1, Korrektur an Abschnitt 4: Eine **allein stehende Jahreszahl zählt** als Zeitraum («Was hat Funiciello 2022 gesagt?», der Ausgangsfall der Spec), ausser sie hängt direkt an einem Titel («Voranschlag 2025», «Armeebotschaft 2024», «Energiestrategie 2050»). Ausdrücklich genannte **Sessionen und Monate zählen auch in der Zukunft** («Frühjahrssession 2027» ergibt `out_of_range`); nur eine allein stehende Jahreszahl nach dem laufenden Jahr wird ignoriert. Das Goldset v3 enthält beide Formen. | Beim Zusammenstellen des Goldsets aufgefallen: Mit Signalwort-Pflicht würde der Fall aus spec.md, Abschnitt 1, nicht erkannt. |
