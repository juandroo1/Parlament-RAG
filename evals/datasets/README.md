# Goldset

`golden.jsonl` enthält die Fragen, an denen die Evals Retrieval und Antworten messen (plan.md, Abschnitt 9). Stand: **Goldset v1** mit 33 Fragen (Task 3.1). Der Ausbau auf 65 Fragen folgt in Task 4.5.

## Schema

Eine Zeile pro Frage, geprüft durch `parlrag.evals.GoldenItem`:

```json
{"id": "q05", "question": "…", "language": "de", "filters": {"council": "SR"},
 "expected_source_ids": ["transcript:422818", "business:20260054"],
 "answerable": true, "tags": ["filter", "teilkorpus", "smoke"], "notes": "…"}
```

| Feld | Bedeutung |
|---|---|
| `id` | `q01` bis `q33`, stabil; neue Fragen bekommen neue Nummern |
| `language` | Sprache der Frage, `de` oder `fr` |
| `filters` | optional, wie in `parlrag search` bzw. `POST /ask`: `council`, `date_from`, `date_to`, `parl_group` |
| `expected_source_ids` | erwartete Dokumente als `<source_type>:<source_id>`, also ein Votum (`transcript:<ID>`) oder ein Geschäftstext (`business:<ID>`), nie Chunks. Bei Geschäften gilt die ID für beide Sprachen |
| `answerable` | `false` nur bei unbeantwortbaren Fragen; dann ohne Quellen |
| `notes` | kurze Begründung, warum genau diese Quellen |

## Tags

| Tag | Bedeutung | Anzahl in v1 |
|---|---|---|
| `fr` | Frage auf Französisch | 8 (5 beantwortbar, 1 wertend, 2 unbeantwortbar) |
| `crosslingual` | erwartete Voten in der anderen Sprache als die Frage (US-5) | 5 |
| `filter` | Frage mit Filter (AK-4.2) | 6 |
| `unanswerable` | Der Korpus enthält keine Antwort (AK-3.2) | 5 |
| `wertend` | Frage verlangt eine Bewertung (AK-7.1) | 3 |
| `teilkorpus` | Quellen in der Herbstsession 2026 (Session 5215), dem Teilkorpus für Experimente | 19 |
| `smoke` | gehört zur Smoke-Suite (`parlrag eval --suite smoke`) | 15 |

Zusammensetzung: 20 beantwortbare Fragen auf Deutsch, 5 auf Französisch, 5 unbeantwortbare und 3 wertende.

## Regeln

- **Konkrete Fragen.** Jede Frage bezieht sich auf eine Person, ein Geschäft oder einen Wortwechsel, sodass ein bis fünf Dokumente sie vollständig beantworten. Aufgeführt sind alle Dokumente, die das tun. Bei breiten Fragen («Was wurde zu X gesagt?») gäbe es Dutzende passende Voten, und Recall@10 wäre nicht aussagekräftig.
- **Aussagen des Bundesrats.** Fragt die Frage nach der Haltung des Bundesrats, gelten seine Voten und die Stellungnahme im Geschäftstext als erwartet. Fraktionsvoten, die den Punkt nur wiederholen, zählen nicht.
- **Wertende Fragen** beziehen sich auf eine Vorlage im Korpus. Erwartet ist, dass das System die Positionen wiedergibt (Kommissionssprechende, Bundesrat, Minderheit) oder ablehnt, aber nicht selbst wertet. Sie gelten als beantwortbar, zählen aber nicht zu den falschen Ablehnungen (AK-3.3).
- **Unbeantwortbare Fragen** liegen nach dem Stichtag 2026-10-02, vor dem Korpus (vor Dezember 2023), auf kommunaler Ebene oder betreffen ein Thema, das im Parlament nie behandelt wurde. Für jede wurde per Volltextsuche geprüft, dass der Korpus nichts dazu enthält.
- **Eingefrorener Korpus.** Alle Quellen stammen aus dem Korpus bis zum Stichtag 2026-10-02 (plan.md, Abschnitt 3, «Korpus-Stand»).

## Herkunft

Die Fragen und Quellen hat Claude aus dem echten Korpus vorgeschlagen: Debatten durchsucht, Voten gelesen, Quellen per Volltextsuche auf Vollständigkeit geprüft. Sandro hat am 2026-11-14 alle 33 Fragen samt Quellen anhand einer Review-Datei mit Ausschnitten und Links geprüft und freigegeben (plan.md, Abschnitt 9: «Ein LLM darf Vorschläge machen, entscheidet aber nicht»).

Ein einmaliger Abgleich mit der lokalen Datenbank hat bestätigt:

- Alle erwarteten Dokumente existieren.
- Bei `crosslingual` sind die Voten in der anderen Sprache.
- Bei `teilkorpus` liegen die Quellen in Session 5215.
- Bei Fragen mit Filter erfüllen alle Quellen den Filter.

In der CI ist die Datenbank leer, deshalb prüfen die Tests (`tests/test_goldset.py`) nur Schema und Zusammensetzung.
