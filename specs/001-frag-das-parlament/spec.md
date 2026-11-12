# Spec 001 – Frag das Parlament

Status: Entwurf · Version 0.2

## 1. Problem

Wer wissen will, was im Bundesparlament zu einem Thema gesagt wurde, durchsucht heute Curia Vista und das Amtliche Bulletin von Hand. Die Stichwortsuche findet Wörter, beantwortet aber keine Fragen wie «Welche Argumente wurden im Ständerat zum Ausbau der Bahninfrastruktur vorgebracht?». Französische Voten findet man mit deutschen Suchbegriffen gar nicht.

## 2. Ziel

Eine Anwendung, die natürlichsprachige Fragen auf Deutsch oder Französisch beantwortet. Sie stützt sich ausschliesslich auf Ratsprotokolle und Geschäftstexte und belegt jede Aussage mit einer klickbaren Quelle. Die Qualität wird mit einem reproduzierbaren Eval-Set gemessen und im README ausgewiesen.

Nebenziel: Das Projekt dient als Portfolio-Nachweis für RAG, hybride Suche, Evals und sauberes Engineering.

## 3. Zielgruppe

- Interessierte Bürgerinnen und Bürger, Studierende, Journalistinnen und Journalisten.
- Persona: Lea, 23, studiert Politikwissenschaft und schreibt eine Arbeit über Verkehrspolitik. Sie will schnell wissen, wer was gesagt hat, und die Originalstelle prüfen können.

## 4. User Stories und Akzeptanzkriterien

### US-1 Frage stellen
Als Nutzerin will ich eine Frage auf Deutsch oder Französisch stellen und eine zusammenhängende Antwort erhalten.

- AK-1.1: Die Antwort ist in der Sprache der Frage verfasst.
- AK-1.2: Jede inhaltliche Aussage verweist auf mindestens eine Quelle im Format [n].
- AK-1.3: Die Antwortzeit liegt bei p95 unter 10 Sekunden.

### US-2 Quellen prüfen
Als Nutzerin will ich zu jeder Quelle sehen, woher sie stammt.

- AK-2.1: Jede Quelle zeigt Redner/in, Fraktion, Rat, Datum, Geschäftsnummer (falls vorhanden) und einen Textausschnitt.
- AK-2.2: Jede Quelle verlinkt auf die Originalstelle auf parlament.ch.
- AK-2.3: Jede in der Antwort zitierte Quelle wurde tatsächlich als Kontext übergeben. Erfundene Quellen-IDs sind technisch ausgeschlossen.

### US-3 Keine Grundlage
Als Nutzerin will ich ehrlich hören, wenn es zu meiner Frage nichts Passendes gibt.

- AK-3.1: Findet das System keine ausreichenden Quellen, antwortet es mit einem klaren Hinweis statt mit einer erfundenen Antwort.
- AK-3.2: Auf dem Teilset «unbeantwortbar» lehnt das System mindestens 90 % korrekt ab.
- AK-3.3: Auf den beantwortbaren Fragen wird die Quote falscher Ablehnungen gemessen und ausgewiesen. Der Zielwert wird nach der Baseline festgelegt.

### US-4 Filter
Als Nutzerin will ich nach Rat, Zeitraum und Fraktion filtern.

- AK-4.1: Filter wirken bereits beim Retrieval, nicht erst nachträglich auf die Treffer.
- AK-4.2: Mit Filter enthält die Antwort ausschliesslich Quellen, die den Filter erfüllen.
- AK-4.3: Für Geschäfte (Curia Vista) gilt:
  - Zeitraum: Ein Geschäft erfüllt den Filter, wenn es im Zeitraum mindestens einmal im Rat debattiert wurde. Das Einreichungsdatum wird angezeigt, aber nicht gefiltert.
  - Rat: Ein Geschäft erfüllt den Filter, wenn es in diesem Rat debattiert wurde.
  - Fraktion: Bei einem Fraktionsfilter fallen Geschäfte weg; es zählen nur Voten von Mitgliedern dieser Fraktion.
  - Bekannte Grenze: Zeitraum und Rat werden bei Geschäften unabhängig geprüft. Ein Geschäft, das 2024 im Nationalrat und 2025 im Ständerat debattiert wurde, erfüllt auch «Ständerat + 2024».

### US-5 Sprachübergreifende Suche
Als Nutzerin will ich mit einer deutschen Frage auch relevante französische Voten finden (und umgekehrt).

- AK-5.1: Auf dem Teilset «sprachübergreifend» wird Recall@10 gemessen und ausgewiesen. Der Zielwert wird nach der Baseline festgelegt.

### US-6 Evals (Entwickler)
Als Entwickler will ich mit einem Befehl alle Evals ausführen und das Ergebnis mit dem letzten Lauf vergleichen.

- AK-6.1: `parlrag eval --suite smoke|full` schreibt die Ergebnisse mit Git-SHA und Konfiguration nach `evals/results/`.
- AK-6.2: Die Ausgabe zeigt pro Metrik die Differenz zum vorherigen Lauf.

### US-7 Neutralität
Als Nutzerin will ich mich darauf verlassen können, dass das System wiedergibt, was gesagt wurde, und nicht selbst wertet.

- AK-7.1: Auf dem Teilset «wertend» (z. B. «Ist Partei X gut?») gibt das System keine eigene Bewertung von Personen, Parteien oder Vorlagen ab. Es gibt wieder, was im Parlament dazu gesagt wurde, oder lehnt ab. Gemessen per LLM-as-Judge; der Zielwert wird nach der Baseline festgelegt.

## 5. Datenumfang (MVP)

- Wortprotokolle (Amtliches Bulletin) von Nationalrat und Ständerat ab Beginn der 52. Legislatur (Wintersession 2023) bis heute.
- Geschäfte aus Curia Vista mit Titel, eingereichtem Text, Antwort des Bundesrates und Status, sofern sie im Zeitraum behandelt wurden.
- Sprachen: Deutsch und Französisch.
- Für Evals gilt ein eingefrorener Korpus bis zu einem festen Stichtag (festgelegt in Task 2.6), damit Läufe über die Zeit vergleichbar bleiben. Experimente laufen auf einem festen Teilkorpus von zwei bis drei Sessions.

## 6. Qualitätsziele

| Metrik | Beschreibung | Ziel MVP |
|---|---|---|
| Recall@10 | Anteil erwarteter Quellen unter den Top 10 | ≥ 0.80 |
| MRR@10 | Rang des ersten relevanten Treffers | Baseline messen, darf nicht sinken |
| Zitiergenauigkeit | Aussage wird vom zitierten Abschnitt gestützt (LLM-as-Judge, stichprobenweise von Hand geprüft) | ≥ 0.90 |
| Ablehnungsquote | Korrekte Ablehnung bei unbeantwortbaren Fragen | ≥ 0.90 |
| Falsche Ablehnungen | Anteil abgelehnter beantwortbarer Fragen | Baseline messen, Ziel danach festlegen |
| Neutralität | Keine eigene Wertung auf dem Teilset «wertend» (LLM-as-Judge) | Baseline messen, Ziel danach festlegen |
| Antwortsprache | Antwort in der Sprache der Frage (AK-1.1, automatisch erkannt) | gemessen und ausgewiesen |
| Latenz | p95 pro Frage | < 10 s |
| Kosten | Durchschnittliche Kosten pro Frage | gemessen und im README ausgewiesen |

Goldset (Endstand MVP): mindestens 65 Fragen, davon 40 auf Deutsch und 10 auf Französisch beantwortbar (mindestens 10 davon sprachübergreifend), 10 unbeantwortbare und 5 wertende. Die Fragen und die erwarteten Quellen werden von Hand bestimmt. Erwartete Quellen werden als Dokumente angegeben (ein Votum oder ein Geschäftstext), nicht als Chunks.

## 7. Nicht-Ziele

- Keine Bewertung von Personen, Parteien oder Vorlagen, keine Abstimmungsempfehlungen.
- Keine Auswertung von Abstimmungsresultaten (mögliche spätere Spec).
- Keine Benutzerkonten und keine gespeicherten Chatverläufe.
- Keine kantonalen oder kommunalen Parlamente.
- Kein Italienisch im MVP.
- Kein Fine-Tuning.

## 8. Offene Fragen

- Lizenz und Nutzungsbedingungen der Daten für eine öffentliche Demo verifizieren.
- Lokales Embedding-Modell oder API-Modell: per Eval entscheiden (Qualität gegen Kosten).
- Hosting der Demo und Schutz vor Missbrauch (Rate-Limit, Kostendeckel).
- Mehrturn-Gespräche (Folgefragen) für eine spätere Version?
- Seitenzahl im Amtlichen Bulletin (Platzhalter `[PAGE n]` im Votum) als zusätzliche Quellenangabe in einer späteren Version?
- Deployment unter Linux (Task 6.3): Der Container-User (UID 10001) darf im Bind-Mount `./data/raw` eventuell nicht schreiben. Lösung beim Deployment festlegen (Besitzrechte des Ordners oder benanntes Volume).