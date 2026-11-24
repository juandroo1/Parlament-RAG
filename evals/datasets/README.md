# Goldset

`golden.jsonl` enthält die Fragen, an denen die Evals Retrieval und Antworten messen (plan.md, Abschnitt 9). Stand: **Goldset v3** mit 80 Fragen: v1 mit 33 Fragen aus Task 3.1, ausgebaut in Task 4.5b auf 65 Fragen (v2, Endstand MVP, Spec 001, Abschnitt 6), ergänzt in Task 8.1 um 15 Fragen mit Person oder Zeitraum (Spec 003, AK-19.1).

## Schema

Eine Zeile pro Frage, geprüft durch `parlrag.evals.GoldenItem`:

```json
{"id": "q05", "question": "…", "language": "de", "filters": {"council": "SR"},
 "expected_source_ids": ["transcript:422818", "business:20260054"],
 "answerable": true, "tags": ["filter", "teilkorpus", "smoke"], "notes": "…"}
```

| Feld | Bedeutung |
|---|---|
| `id` | `q01` bis `q80`, stabil; neue Fragen bekommen neue Nummern (v1: `q01` bis `q33`, v2: bis `q65`, v3: bis `q80`) |
| `language` | Sprache der Frage, `de` oder `fr` |
| `filters` | optional, wie in `parlrag search` bzw. `POST /ask`: `council`, `date_from`, `date_to`, `parl_group` |
| `expected_source_ids` | erwartete Dokumente als `<source_type>:<source_id>`, also ein Votum (`transcript:<ID>`) oder ein Geschäftstext (`business:<ID>`), nie Chunks. Bei Geschäften gilt die ID für beide Sprachen |
| `answerable` | `false` nur bei unbeantwortbaren Fragen; dann ohne Quellen |
| `notes` | kurze Begründung, warum genau diese Quellen |

## Tags

| Tag | Bedeutung | Anzahl |
|---|---|---|
| `fr` | Frage auf Französisch | 21 (14 beantwortbar, 2 wertend, 5 unbeantwortbar) |
| `crosslingual` | erwartete Voten in der anderen Sprache als die Frage (US-5) | 12 |
| `filter` | Frage mit Filter (AK-4.2) | 8 |
| `unanswerable` | Der Korpus enthält keine Antwort (AK-3.2) | 14 |
| `wertend` | Frage verlangt eine Bewertung (AK-7.1) | 5 |
| `teilkorpus` | Quellen in der Herbstsession 2026 (Session 5215), dem Teilkorpus für Experimente | 23 |
| `smoke` | gehört zur Smoke-Suite (`parlrag eval --suite smoke`); unverändert seit v1, damit Smoke-Läufe vergleichbar bleiben | 15 |
| `person-zeit` | Frage nennt eine Person und/oder einen Zeitraum (Spec 003, US-19); darunter ein mehrdeutiger Name («Müller») und ein Name im Titel («Initiative Funiciello») | 17 (11 beantwortbar, 6 ausserhalb) |
| `ausserhalb` | Zeitraum liegt ausserhalb des Datenbestands (Voten vom 4. Dezember 2023 bis 2. Oktober 2026); immer unbeantwortbar, erwartet ist der Hinweis `out_of_range` ohne LLM-Aufruf (AK-16.1) | 6 |

Zusammensetzung: 47 beantwortbare Fragen auf Deutsch, 14 auf Französisch, 14 unbeantwortbare und 5 wertende. Die Fragen aus v2 verteilen sich über die Sessionen von Dezember 2023 bis Oktober 2026; mehrere beziehen sich nur auf Geschäftstexte. Die Fragen aus v3 betreffen meist Themen, zu denen dieselbe Person in mehreren Sessionen sprach (z. B. die jährliche Staatsrechnung), damit Person und Zeitraum über die richtige Quelle entscheiden.

## Regeln

- **Konkrete Fragen.** Jede Frage bezieht sich auf eine Person, ein Geschäft oder einen Wortwechsel, sodass ein bis fünf Dokumente sie vollständig beantworten. Aufgeführt sind alle Dokumente, die das tun. Bei breiten Fragen («Was wurde zu X gesagt?») gäbe es Dutzende passende Voten, und Recall@10 wäre nicht aussagekräftig.
- **Aussagen des Bundesrats.** Fragt die Frage nach der Haltung des Bundesrats, gelten seine Voten und die Stellungnahme im Geschäftstext als erwartet. Fraktionsvoten, die den Punkt nur wiederholen, zählen nicht.
- **Wertende Fragen** beziehen sich auf eine Vorlage im Korpus. Erwartet ist, dass das System die Positionen wiedergibt (Kommissionssprechende, Bundesrat, Minderheit) oder ablehnt, aber nicht selbst wertet. Sie gelten als beantwortbar, zählen aber nicht zu den falschen Ablehnungen (AK-3.3).
- **Unbeantwortbare Fragen** liegen nach dem Stichtag 2026-10-02, vor dem Korpus (vor Dezember 2023), auf kommunaler Ebene oder betreffen ein Thema, das im Parlament nie behandelt wurde. Nennen sie einen Zeitraum ausserhalb des Korpus, tragen sie den Tag `ausserhalb`. Für jede wurde per Volltextsuche geprüft, dass der Korpus nichts dazu enthält.
- **Eingefrorener Korpus.** Alle Quellen stammen aus dem Korpus bis zum Stichtag 2026-10-02 (plan.md, Abschnitt 3, «Korpus-Stand»).

## Herkunft

Die Fragen und Quellen hat Claude aus dem echten Korpus vorgeschlagen: Debatten durchsucht, Voten gelesen, Quellen per Volltextsuche auf Vollständigkeit geprüft. Sandro hat am 2026-11-14 alle 33 Fragen von v1 und danach die 32 neuen Fragen von v2 samt Quellen anhand je einer Review-Datei mit Ausschnitten und Links geprüft und freigegeben (plan.md, Abschnitt 9: «Ein LLM darf Vorschläge machen, entscheidet aber nicht»). Die 15 Fragen von v3 (q66 bis q80) samt Quellen hat Sandro am 2026-11-24 ebenso anhand einer Review-Datei geprüft und freigegeben.

Ein einmaliger Abgleich mit der lokalen Datenbank hat bestätigt:

- Alle erwarteten Dokumente existieren.
- Bei `crosslingual` sind die Voten in der anderen Sprache.
- Bei `teilkorpus` liegen die Quellen in Session 5215.
- Bei Fragen mit Filter erfüllen alle Quellen den Filter.

In der CI ist die Datenbank leer, deshalb prüfen die Tests (`tests/test_goldset.py`) nur Schema und Zusammensetzung.
