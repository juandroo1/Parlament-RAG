# Spec 003 – Person und Zeitraum aus der Frage

Status: Freigegeben · Version 1.0

Baut auf [Spec 001](../001-frag-das-parlament/spec.md) und [Spec 002](../002-redesign/spec.md) auf. Architektur, Daten, Leitplanken und alle Akzeptanzkriterien gelten weiter. User Stories und Akzeptanzkriterien sind fortlaufend nummeriert (ab US-16), Tasks als Phase 8 (8.x).

## 1. Problem

Wer fragt «Was hat Tamara Funiciello 2022 gesagt?», bekommt heute nur «Keine ausreichende Grundlage», ohne zu erfahren, warum. Dahinter stecken zwei Lücken:

1. **Der Datenbestand ist nicht sichtbar.** Die Voten beginnen am 4. Dezember 2023 (Beginn der 52. Legislatur). Eine Frage zu 2022 kann das System nicht beantworten. Es sucht trotzdem, ruft das Modell auf (Kosten) und meldet dann nur eine allgemeine Ablehnung.
2. **Person und Zeitraum in der Frage werden nicht verstanden.** Die Suche vergleicht nur die Bedeutung von Frage und Abschnitt. Name und Jahr wirken nicht als Filter. Das Beispiel oben findet Voten von Funiciello aus allen Jahren, aber auch Voten anderer über die «Initiative Funiciello». Einen Filter nach Person gibt es gar nicht.

## 2. Ziel

- Fragen ausserhalb des Datenbestands werden sofort und verständlich beantwortet: was fehlt und welchen Zeitraum die Daten abdecken. Ohne Aufruf des Modells.
- Nennt eine Frage eine Person oder einen Zeitraum, sucht das System gezielt in deren Voten bzw. in diesem Zeitraum. Die Nutzerin sieht, welche Filter erkannt wurden, und kann sie entfernen.
- Wer gezielt filtern will, kann in der Oberfläche auch eine Person wählen.
- Die Wirkung wird mit Evals gemessen: besser auf Fragen mit Person oder Zeitraum, nicht schlechter auf den übrigen.

## 3. Zielgruppe

Wie Spec 002: interessierte Bürgerinnen und Bürger, oft auf dem Handy. Typische Fragen nennen eine Person («Was sagte Bundesrat Rösti zu …?», «Qu’a dit Céline Amaudruz sur …?») oder eine Zeit («im Herbst 2025», «seit 2024», «in der Wintersession 2023»).

## 4. User Stories und Akzeptanzkriterien

### US-16 Datenbestand
Als Nutzerin will ich erfahren, wenn meine Frage ausserhalb der vorhandenen Daten liegt, und welchen Zeitraum die Daten abdecken.

- AK-16.1: Liegt der erkannte oder als Filter gesetzte Zeitraum ganz ausserhalb der Voten im Korpus, antwortet das System ohne Suche und ohne LLM-Aufruf mit einem eigenen Hinweis: Die Daten reichen vom [erstes Datum] bis [letztes Datum]. Grund in der API: `out_of_range`.
- AK-16.2: Überlappt der Zeitraum nur teilweise (z. B. «seit 2022»), sucht das System im abgedeckten Teil und weist unter der Antwort darauf hin, ab wann Daten vorliegen.
- AK-16.3: Der abgedeckte Zeitraum stammt aus der Datenbank (erstes und letztes Datum der Voten), nicht aus fest eingetragenen Werten. Nach einem neuen Ingest stimmt er ohne Codeänderung.
- AK-16.4: Hinweis und Zeitraum erscheinen in der Web-UI auf Deutsch und Französisch, mit Datum im Format der Sprache.

### US-17 Person und Zeitraum erkennen
Als Nutzerin will ich einfach fragen «Was sagte X 2025 zu Y?» und Antworten aus den Voten von X aus diesem Jahr bekommen.

- AK-17.1: Das System erkennt in deutschen und französischen Fragen:
  - Personen, die im Korpus Voten haben: Nachname allein, wenn er eindeutig ist, sonst Vor- und Nachname; auch mit Funktion («Bundesrat Rösti», «conseillère nationale Funiciello»).
  - Zeitangaben: Jahr («2025», «en 2024»), Monat und Jahr («im März 2025»), Session («Herbstsession 2025», «session d’automne 2025»), offene Bereiche («seit 2024», «vor 2025», «zwischen 2024 und 2025»).
- AK-17.2: Erkannte Person und erkannter Zeitraum wirken wie ausdrücklich gesetzte Filter beim Retrieval (AK-4.1). Ausdrücklich gesetzte Filter haben Vorrang vor erkannten.
- AK-17.3: Ist ein Name mehrdeutig (z. B. «Müller»: Damian Müller und Leo Müller), filtert das System nicht nach Person und zeigt die möglichen Personen zur Auswahl.
- AK-17.4: Wird eine Person nur als Teil eines Titels genannt (z. B. «Initiative Funiciello»), darf der Filter nicht zu einer falschen Ablehnung führen: Findet die Suche mit dem erkannten Personenfilter keine ausreichenden Quellen, sucht das System ohne diesen Filter noch einmal und sagt das. Die genaue Regel legt der Plan fest; die Evals messen sie.
- AK-17.5: Die API gibt die angewandten Filter zurück und kennzeichnet, welche erkannt und welche gesetzt wurden. Die Web-UI zeigt erkannte Filter über der Antwort («Gesucht in: Voten von Tamara Funiciello · 2025») mit einer Möglichkeit, sie zu entfernen und ohne sie neu zu fragen.
- AK-17.6: Die Erkennung braucht keinen zusätzlichen Aufruf eines LLM und keine externen Dienste. Sie ist in Tests ohne Datenbank und ohne Netz prüfbar (Liste der Personen als Eingabe).

### US-18 Filter «Person»
Als Nutzerin will ich in den Filtern gezielt eine Person wählen.

- AK-18.1: Die Filter in der Web-UI erhalten ein Feld «Person» mit Vorschlägen beim Tippen (Name, Fraktion, Kanton bzw. «Bundesrat»), auf Deutsch und Französisch, per Tastatur bedienbar (AK-13.2).
- AK-18.2: Die API und `parlrag search|ask` nehmen den Filter `speaker` an. Mit Personenfilter fallen Geschäftstexte weg, wie beim Fraktionsfilter (AK-4.3).
- AK-18.3: Mit Personenfilter enthält die Antwort ausschliesslich Voten dieser Person (wie AK-4.2).

### US-19 Messen (Entwickler)
Als Entwickler will ich sehen, ob die Erkennung die Antworten verbessert und nichts verschlechtert.

- AK-19.1: Das Goldset bekommt ein neues Teilset `person-zeit` mit mindestens 10 beantwortbaren Fragen, die eine Person und/oder einen Zeitraum nennen, und mindestens 3 Fragen ausserhalb des Datenbestands (Teilset `ausserhalb`). Claude schlägt sie aus dem Korpus vor, Sandro prüft jede Frage (wie in Spec 001). Die Smoke-Suite bleibt unverändert.
- AK-19.2: Vor der Umsetzung wird eine Baseline auf dem neuen Teilset gemessen, danach derselbe Lauf mit Erkennung. Der Vergleich steht in der PR-Beschreibung und im README.
- AK-19.3: Die Erkennung ist abschaltbar (Konfiguration), damit Läufe mit und ohne sie vergleichbar sind.

## 5. Datenumfang

Unverändert: Voten ab Wintersession 2023, Geschäfte aus Curia Vista, Deutsch und Französisch. Ältere Daten zu laden ist nicht Teil dieser Spec (Offene Fragen).

## 6. Qualitätsziele

| Metrik | Beschreibung | Ziel |
|---|---|---|
| Recall@10 `person-zeit` | erwartete Quellen unter den Top 10, Teilset mit Person oder Zeitraum | deutlich über der Baseline ohne Erkennung (Zielwert nach der Baseline festlegen) |
| Recall@10, MRR@10 gesamt | alle übrigen Fragen | nicht schlechter als der letzte Lauf |
| Falsche Ablehnungen | beantwortbare Fragen, die abgelehnt werden | höchstens 0.05 (wie Spec 001) |
| `ausserhalb` | Fragen ausserhalb des Datenbestands mit Grund `out_of_range` und ohne LLM-Aufruf | 100 % |
| Erkennung | Person und Zeitraum auf einer Liste von Testfragen (Unit-Tests) | alle Testfälle korrekt |
| Latenz | zusätzliche Zeit für die Erkennung | unter 50 ms pro Frage |
| Kosten | zusätzliche Kosten pro Frage | keine; Fragen ausserhalb sparen den LLM-Aufruf |

## 7. Nicht-Ziele

- Keine älteren Daten (vor der 52. Legislatur) in dieser Spec.
- Kein zusätzlicher LLM-Aufruf, um die Frage zu verstehen.
- Keine Erkennung von Fraktion, Partei oder Rat aus der Frage (Offene Fragen); die bestehenden Filter bleiben.
- Keine Folgefragen und kein Gesprächsverlauf.
- Keine Auswertung, wer wie oft gesprochen hat (Statistik).

## 8. Offene Fragen

- Fraktion und Rat aus der Frage erkennen («Was sagte die SVP …?», «im Ständerat»)? Gleiche Technik, aber Parteien und Fraktionen sind nicht dasselbe (z. B. Mitte-Fraktion mit EVP).
- Ältere Daten, etwa die 51. Legislatur ab Dezember 2019: mehr Speicher auf dem Server, längere Indexierung, Goldset nachziehen.
- Erkennung per LLM, falls die Regeln an Grenzen stossen (Kosten und Latenz gegen Trefferquote abwägen).
- Fragen mit Person und Zeitraum, aber ohne Thema («Was sagte X 2025?»): die Themen auflisten, zu denen die Person in diesem Zeitraum gesprochen hat, statt abzulehnen?
- Personen, die nicht im Korpus sprechen (z. B. ehemalige Ratsmitglieder): eigener Hinweis «zu dieser Person gibt es keine Voten im Datenbestand»?
