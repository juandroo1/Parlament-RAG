# Plan 001 – Frag das Parlament

Bezieht sich auf: `spec.md` Version 0.2

## 1. Architektur

```
parlament.ch OData ──► Ingestion ──► data/raw/ (JSON-Cache)
                            │
                            ▼
                     Postgres: documents
                            │
                  Chunking + Embedding
                            ▼
              Postgres: chunks (tsvector + vector)
                            │
Frage ──► API/CLI ──► Retriever ──► Generator (Claude) ──► Antwort + Quellen
                      (FTS + Vektor
                       → RRF → opt. Rerank)

Eval-Runner nutzt dieselben Komponenten wie API und CLI.
```

## 2. Tech-Stack

| Bereich | Wahl | Begründung |
|---|---|---|
| Sprache | Python 3.12, uv | Standard im AI-Engineering, schnelles Dependency-Management |
| API | FastAPI, Pydantic v2 | Typisiert, schnell, gute Doku |
| Datenbank | PostgreSQL 16 + pgvector | Volltext und Vektoren in einer DB, kein zusätzlicher Dienst |
| Migrationen | Alembic | Nachvollziehbares Schema |
| Embeddings | BAAI/bge-m3 lokal (sentence-transformers, PyTorch CPU-Build), 1024 Dimensionen, Modell wird erst bei Bedarf geladen | Mehrsprachig (DE/FR), kostenlos; das Interface erlaubt einen Vergleich mit einem API-Modell |
| Volltext | Postgres `tsvector` mit Konfiguration `german` bzw. `french` je nach Sprache | Stemming pro Sprache |
| Fusion | Reciprocal Rank Fusion (k = 60) | Einfach, robust, ohne Score-Normalisierung |
| Reranker (optional) | BAAI/bge-reranker-v2-m3 | Nur einbauen, wenn die Evals einen Gewinn zeigen |
| LLM | Claude Opus 5.5 (`claude-opus-5-5`, Effort `high`) über das Anthropic Python SDK; Modell und Effort über `ANTHROPIC_MODEL` und `ANTHROPIC_EFFORT` | Konfigurierbar, gut für Vergleiche |
| CLI | Typer | |
| Frontend | React + Vite + Tailwind (Phase 5) | Bekannter Stack |
| Qualität | pytest, ruff, mypy, GitHub Actions | |
| Container | Docker Compose mit `db`, `app`, `web` | Ein Befehl startet alles, lokal und in der Demo identisch |
| Observability | structlog mit Tokens, Latenz und Kosten pro Anfrage | Produktionsdenken sichtbar machen |

## 3. Datenquelle

- OData-v3-Endpunkt: `https://ws.parlament.ch/odata.svc/`, ohne API-Key. Das Schema steht unter `$metadata`.
- Relevante Entitäten (in Task 0.2 zu verifizieren): `Session`, `Meeting`, `Subject`, `Transcript`, `Business`, `MemberCouncil`. Die Kette Session → Meeting → Subject → Transcript führt zu den Wortprotokollen.
- Die Sprache wird über das Feld `Language` gesteuert (`DE`, `FR`). Zu prüfen in Task 0.2: Vermutlich ist `Language` nur die Sprache der Metadaten, und ein Votum liegt nur in der Originalsprache vor (Feld `LanguageOfText`). Dann würde das Laden von DE und FR doppelte Voten erzeugen.
- Paginierung mit `$top`/`$skip`, kurze Pausen zwischen Requests, Retry mit exponentiellem Backoff.
- Transcript-Texte können Markup enthalten. Die Bereinigung erfolgt in einer eigenen, getesteten Funktion.
- Das Schema ist nur teilweise dokumentiert. Deshalb wird nie direkt gegen die Live-API getestet, sondern gegen gespeicherte Fixtures.

## 4. Datenmodell

```
documents
  id              uuid pk
  source_type     text  -- 'transcript' | 'business'
  source_id       text  -- ID aus OData
  language        text  -- 'de' | 'fr'
  title           text
  text            text
  speaker_name    text null
  parl_group      text null
  council         text null  -- 'NR' | 'SR' | 'VB'
  date            date
  business_number text null
  url             text
  raw_hash        text  -- für idempotente Ingestion
  unique (source_type, source_id, language)

chunks
  id           uuid pk
  document_id  uuid fk
  chunk_index  int
  language     text
  text         text
  token_count  int
  tsv          tsvector
  embedding    vector(1024)
  metadata     jsonb
```

Eval-Läufe werden nicht in der Datenbank gespeichert, sondern als Dateien in `evals/results/` (Abschnitt 9).

Indizes: GIN auf `chunks.tsv`, HNSW auf `chunks.embedding` (Cosine), B-Tree auf `documents(date, council, parl_group)`.

## 5. Chunking

- Transcripts: Ein Votum ist die natürliche Einheit. Kurze Voten bleiben ganz, lange werden an Absatzgrenzen in Stücke von etwa 400–600 Tokens mit etwa 15 % Overlap geteilt.
- Vor dem Einbetten erhält jeder Chunk einen Kontext-Header, z. B. `Ständerat · 12.03.2025 · Max Muster (FDP-Liberale Fraktion) · Geschäft 24.123 – Titel`. Gespeichert wird der Chunk ohne Header, eingebettet mit Header.
- Geschäfte: Titel, eingereichter Text und Antwort des Bundesrates werden als getrennte Chunks gespeichert.

## 6. Retrieval

1. Filter (Rat, Zeitraum, Fraktion) als SQL-`WHERE`, angewendet vor der Suche.
2. Volltext Top 50 und Vektor Top 50.
3. RRF, daraus die Top 20.
4. Optional ein Reranker auf die Top 8 (Entscheid per Eval, Task 6.1).
5. Liegt der beste Score unter einem Schwellwert, wird «keine ausreichende Grundlage» gemeldet. Der Schwellwert wird auf dem Goldset kalibriert. Achtung: Der RRF-Score hängt nur vom Rang ab und taugt nicht als Schwelle. Massgeblich ist die Cosine-Similarity des besten Vektortreffers oder, falls vorhanden, der Reranker-Score.

## 7. Generierung

- Der System-Prompt (`prompts/answer.md`) verlangt: nur aus den Quellen antworten, Quellen als [n] referenzieren, in der Sprache der Frage antworten, neutral bleiben und Lücken offen benennen.
- Die Quellen werden dem Modell nummeriert übergeben ([1] bis [k]). Das Modell sieht keine Chunk-IDs.
- Strukturierte Ausgabe über ein Pydantic-Schema:
  ```
  { answer: str, citations: [int], insufficient_context: bool }
  ```
- Der Server ordnet jede Nummer dem übergebenen Chunk zu. Validierung: Jede Nummer liegt zwischen 1 und k, und jedes [n] im Antworttext steht auch in `citations`. Andernfalls ein Retry, danach ein sauberer Fehler.
- Pro Anfrage werden Input- und Output-Tokens, Latenz und geschätzte Kosten (USD) geloggt.

## 8. API

```
POST /ask
  in:  { question: str, filters?: { council?, date_from?, date_to?, parl_group? } }
  out: { answer, sources: [...], insufficient_context,
         usage: { input_tokens, output_tokens, cost_usd, latency_ms } }

GET /health
```

## 9. Evals

- Datensatz `evals/datasets/golden.jsonl`, eine Zeile pro Frage:
  ```
  { id, question, language, filters?, expected_source_ids: [...], answerable: bool, tags: [...] }
  ```
  Tags z. B. `fr`, `crosslingual`, `filter`, `unanswerable`, `wertend`.
- `expected_source_ids` verweisen auf Dokumente im Format `<source_type>:<source_id>` (ein Votum oder ein Geschäftstext), nie auf Chunk-IDs. Für Recall@k werden die Treffer auf Dokumente dedupliziert.
- Evals laufen gegen den eingefrorenen Korpus (Stichtag aus Task 2.6). Experimente laufen auf dem festen Teilkorpus.
- Retrieval-Metriken sind deterministisch: Recall@k, MRR@10.
- Antwort-Metriken: Zitiergenauigkeit und Faithfulness über LLM-as-Judge (`prompts/judge.md`). Etwa 10 % werden von Hand gegengeprüft und die Übereinstimmung wird dokumentiert.
- Verhaltensmetriken: Ablehnungsquote (unbeantwortbar), Quote falscher Ablehnungen (beantwortbar), Neutralität (Teilset `wertend`, LLM-as-Judge), Antwortsprache (deterministisch per Spracherkennung), Latenz p95.
- Evals laufen nur lokal mit `uv run parlrag eval`, nicht im Container. So sind der Git-SHA verfügbar und die Ergebnisse direkt im Repo.
- Suites: `smoke` (ca. 15 Fragen, schnell und günstig) und `full` (alle Fragen).
- Ergebnisse werden als `evals/results/<datum>_<sha>.json` gespeichert, dazu eine Markdown-Zusammenfassung mit Vergleich zum vorherigen Lauf.
- Goldset-Erstellung: Fragen und erwartete Quellen bestimmt ein Mensch. Ein LLM darf Vorschläge machen, entscheidet aber nicht.

## 10. Geplante Experimente (Ergebnistabelle fürs README)

| Experiment | Varianten |
|---|---|
| Suchverfahren | nur Volltext · nur Vektor · Hybrid (RRF) · Hybrid + Reranker |
| Kontext-Header | mit · ohne |
| Chunkgrösse | ~300 · ~500 · ~800 Tokens |
| Embedding-Modell | bge-m3 lokal · ein API-Modell |

## 11. Risiken

| Risiko | Massnahme |
|---|---|
| OData-Schema ist undokumentiert oder ändert sich | Rohdaten-Cache, Mapping-Tests mit Fixtures |
| Embeddings auf der CPU dauern lange | Zuerst eine Session indexieren, dann ausbauen; Batch-Verarbeitung |
| Kosten durch LLM-as-Judge | `smoke`-Suite klein halten, `full` nur bei grösseren Änderungen |
| Missbrauch der öffentlichen Demo | Rate-Limit, Tageskostendeckel |
| Opus 5.5 mit Effort `high` überschreitet p95 < 10 s (Thinking lässt sich bei Opus 5.5 nicht abschalten) | Latenz in jedem Eval-Lauf messen; bei Überschreitung Effort oder Modell per Eval vergleichen und im Entscheidungsprotokoll festhalten |

## 12. Entscheidungsprotokoll

| Datum | Entscheidung | Grund |
|---|---|---|
| 2026-11-12 | OData-Erkundung (bisher 1.1) wird zu Task 0.2, vor Docker und Alembic. Tasks neu nummeriert. | Das Datenmodell hängt davon ab, was OData liefert (Sprachfelder, Fraktion, Deep-Links). Die Migration soll erst danach entstehen. |
| 2026-11-12 | Neuer Task 2.6: vollständiger Ingest und Index bis zu einem festen Stichtag. | Das Goldset braucht den ganzen Korpus; der Testlauf in 1.4 umfasst nur eine Session. |
| 2026-11-12 | Eval-Korpus wird auf einen Stichtag eingefroren. Experimente (Abschnitt 10) laufen auf einem festen Teilkorpus von zwei bis drei Sessions. | Ein wachsender Korpus macht Läufe unvergleichbar. Eine Neuindexierung des ganzen Korpus dauert auf der CPU Stunden. |
| 2026-11-12 | `expected_source_ids` verweisen auf Dokumente (Votum bzw. Geschäftstext), nicht auf Chunks. Recall wird über deduplizierte Dokumente berechnet. | Chunk-IDs ändern sich bei jedem Re-Chunking, z. B. im Chunkgrössen-Experiment. |
| 2026-11-12 | Zusätzliche Metriken: Quote falscher Ablehnungen auf beantwortbaren Fragen und Neutralität auf dem neuen Teilset «wertend». | Ohne die Gegenmetrik erreicht ein System, das immer ablehnt, 100 % Ablehnungsquote. Die Leitplanke «neutral» war nicht messbar. |
| 2026-11-12 | Standard-LLM: Claude Opus 5.5 (`claude-opus-5-5`) mit Effort `high`, konfigurierbar über `ANTHROPIC_MODEL` und `ANTHROPIC_EFFORT`. | Entscheid Sandro. Risiko für AK-1.3 (Latenz) siehe Abschnitt 11. |
| 2026-11-12 | Git: Squash-Merge; der PR-Titel ist ein Conventional Commit mit Task-Nummer. Der nächste Task beginnt erst, wenn der vorherige PR gemergt ist. Branch Protection auf `main`. | Saubere Historie auf `main`, keine Konflikte in `tasks.md`, Regel «nie direkt auf main» technisch erzwungen. |
| 2026-11-12 | Reduzierte Definition of Done für Phase 0 (siehe `tasks.md`). | Docker, CI und Branch Protection entstehen erst im Verlauf von Phase 0 und können vorher nicht geprüft werden. |
| 2026-11-12 | Schwelle für «keine ausreichende Grundlage» auf Cosine-Similarity bzw. Reranker-Score statt RRF-Score (Abschnitt 6). | Der RRF-Score hängt nur vom Rang ab und ist für den besten Treffer praktisch immer gleich. |
| 2026-11-12 | Embeddings: bge-m3 lokal über sentence-transformers mit dem CPU-Build von PyTorch (eigener PyTorch-CPU-Index in `pyproject.toml`). Das Modell wird erst bei Bedarf geladen; `GET /health` hängt nicht davon ab. | Ohne CPU-Index zieht uv unter Linux die CUDA-Version (mehrere GB). Laden beim Start würde Startzeit und CI-Smoke-Test belasten. ONNX und API-Modelle verworfen bzw. als Experiment in Abschnitt 10. |
| 2026-11-12 | Zitate: Das LLM liefert nur die Nummern `n` der übergebenen Quellen; der Server ordnet sie den Chunks zu (Abschnitt 7). Native Citations der Claude API vorerst nicht. | Erfundene Quellen-IDs sind so technisch ausgeschlossen (AK-2.3), die Lösung passt zum LLM-Interface und ist gut testbar. Native Citations lassen sich nicht mit strukturierter Ausgabe kombinieren. |
| 2026-11-12 | Tabelle `eval_runs` gestrichen. Eval-Ergebnisse liegen nur als Dateien in `evals/results/`. | Die Dateien werden committet und bilden die Historie. Eine zweite Kopie in der DB müsste synchron gehalten werden und ginge mit `docker compose down -v` verloren. |
| 2026-11-12 | Evals laufen nur lokal mit uv, nicht im Container. | Im Image gibt es kein `.git` (kein Git-SHA), und die Ergebnisse in `evals/results/` sollen direkt committet werden. |
