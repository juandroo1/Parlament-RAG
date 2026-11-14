# Tasks 001 – Frag das Parlament

Immer nur einen Task gleichzeitig bearbeiten. Ein Task ist erst erledigt, wenn die Definition of Done in `CLAUDE.md` erfüllt ist. Der nächste Task beginnt erst, wenn der Pull Request des vorherigen gemergt ist.

Nummerierung angepasst am 2026-11-12 (siehe Entscheidungsprotokoll in `plan.md`).

## Phase 0 – Setup und Erkundung

Reduzierte Definition of Done für Phase 0: Es gilt nur, was schon existiert.

- Docker-Punkte (Compose healthy, Befehle im Container) gelten ab Task 0.3.
- «CI grün» gilt ab Task 0.5.
- Task 0.1 wird direkt auf `main` gepusht, ohne Pull Request.

Tasks:

- [x] 0.1 Repo-Grundgerüst: `git init`, uv, src-Layout `src/parlrag`, ruff, mypy, pytest, `.env.example`, `.gitignore`, `.gitattributes` (`* text=auto eol=lf`), README-Skelett mit Quickstart, MIT-Lizenz. Öffentliches GitHub-Repo `Parlament-RAG` anlegen und ersten Stand auf `main` pushen (Ausnahme vom Branch-Prinzip, da `main` noch nicht existiert). Danach Branch Protection auf `main`: Pull Request nötig, kein Force-Push, keine Löschung, nur Squash-Merge.
- [x] 0.2 OData erkunden: `$metadata` laden, die Kette Session → Meeting → Subject → Transcript sowie `Business` verifizieren. Klären: Bedeutung von `Language` gegenüber `LanguageOfText` bei Transcripts (Duplikate?), Felder für Redner/Fraktion/Rat, Deep-Links auf einzelne Voten (AK-2.2), Datumsfelder bei Geschäften. Ergebnis in plan.md, Abschnitt 3, nachtragen und das Datenmodell (Abschnitt 4) bei Bedarf anpassen. 3–5 echte Antworten als Fixtures in `tests/fixtures/` speichern
- [x] 0.3 Docker: Multi-Stage-Dockerfile (uv, Non-Root), `docker-compose.yml` mit `db` (pgvector) und `app`, Healthchecks, `.dockerignore`. Minimale FastAPI mit `GET /health`, damit `app` etwas zum Starten hat
- [x] 0.4 Alembic-Migration für `documents` und `chunks` gemäss plan.md (nach den Erkenntnissen aus 0.2), automatisch beim Start von `app` ausgeführt
- [x] 0.5 GitHub Actions: ruff, mypy, pytest, `docker compose build` und Smoke-Test auf `/health`. Danach die CI-Checks als Required Status Checks in der Branch Protection von `main` eintragen

## Phase 1 – Ingestion

- [x] 1.1 OData-Client mit Paginierung, Drosselung, Retry und Rohdaten-Cache in `data/raw/`
- [x] 1.2 Mapping und Textbereinigung nach `documents`, getestet mit den Fixtures
- [x] 1.3 CLI `parlrag ingest --since --until --lang`, idempotent über `raw_hash`
- [x] 1.4 Testlauf mit einer Session (DE + FR), Statistik ausgeben (Anzahl Voten, Geschäfte, Zeichen)

## Phase 2 – Indexierung und Retrieval

- [x] 2.1 Chunker gemäss plan.md, Abschnitt 5 (Tests für Grenzen, Overlap, Kontext-Header)
- [x] 2.2 Embedding-Interface und bge-m3-Implementierung mit Batch-Verarbeitung (PyTorch CPU-Build, Modell erst bei Bedarf laden, Cache im Volume `hf-cache`)
- [x] 2.3 CLI `parlrag index`, inkrementell (nur neue oder geänderte Dokumente)
- [x] 2.4 Volltextsuche, Vektorsuche, RRF und Filter
- [x] 2.5 CLI `parlrag search "..."` gibt Treffer mit Scores und Metadaten aus
- [x] 2.6 Vollständiger Ingest und Index bis zu einem festen Stichtag. Stichtag und Teilkorpus für Experimente (eine Session) festlegen und in plan.md festhalten. Die volle Indexierung dauert rund 14 Stunden (bge-m3 auf der CPU) und läuft am besten über Nacht. Laufzeit, Anzahl Dokumente und Chunks sowie DB-Grösse dokumentieren

## Phase 3 – Evals zuerst

- [x] 3.1 Goldset v1: 33 Fragen von Hand schreiben, davon 5 unbeantwortbar, 5 französisch, 5 sprachübergreifend, 3 wertend; mindestens 15 Fragen zielen auf den Teilkorpus (Herbstsession 2026) und tragen den Tag `teilkorpus`; erwartete Quellen als Dokument-IDs (`<source_type>:<source_id>`) bestimmen
- [x] 3.2 Eval-Runner für Retrieval-Metriken (Recall@k, MRR@10) über deduplizierte Dokumente, Ergebnisdateien, Vergleich mit dem letzten Lauf
- [x] 3.3 Baseline: nur Volltext vs. nur Vektor vs. Hybrid messen und den Entscheid ins Entscheidungsprotokoll schreiben

## Phase 4 – Generierung

- [x] 4.1 LLM-Interface und Anthropic-Implementierung mit Erfassung von Tokens, Latenz und Kosten
- [x] 4.2a Claude-Abo als LLM-Backend für die lokale Entwicklung (AK-6.3): `LLM_BACKEND=claude-code` ruft die Claude-Code-CLI auf (`claude -p` mit strukturierter Ausgabe), hinter demselben `LLMClient`-Interface; Standard bleibt `api`
- [x] 4.2 Antwort-Prompt, strukturierte Ausgabe und Zitatvalidierung (AK-2.3): Modell liefert nur Quellennummern, Server ordnet sie den Chunks zu
- [x] 4.3 Logik für «keine ausreichende Grundlage»: Schwellwert (Cosine-Similarity bzw. Reranker-Score, nicht RRF) und Modellsignal, Schwellwert auf dem Goldset kalibrieren
- [x] 4.4 CLI `parlrag ask "..."`
- [ ] 4.5a Judge-Prompt und Antwort-Metriken im Eval-Runner (Zitiergenauigkeit, Faithfulness, Ablehnungsquote, falsche Ablehnungen, Neutralität, Antwortsprache, Latenz p95, Kosten): `parlrag eval --answers`, erster Smoke-Lauf
- [ ] 4.5b Goldset auf 65 Fragen ausbauen (Review wie in 3.1), Baseline-Lauf mit Antworten, Schwelle neu kalibrieren, rund 10 % der Judge-Urteile von Hand gegenprüfen und die Übereinstimmung dokumentieren, Kosten pro Frage im README

## Phase 5 – API und UI

- [ ] 5.1 FastAPI um `POST /ask` erweitern, Request-Logging mit Usage
- [ ] 5.2 React-UI: Frage, Filter, Antwort mit klickbaren Quellen, Hinweis auf Datenquelle und Lizenz
- [ ] 5.3 Service `web` in Compose: React-Build über nginx, `/api` als Proxy auf `app`. Der ganze Stack startet mit `docker compose up -d --build`; Smoke-Test in der CI erweitern

## Phase 6 – Optimierung und Portfolio

- [ ] 6.1 Experimente gemäss plan.md, Abschnitt 10, auf dem Teilkorpus durchführen und dokumentieren
- [ ] 6.2 README: Architekturdiagramm, Ergebnistabelle, Designentscheide, Kosten und Latenz, bekannte Grenzen, Hinweis auf den SDD-Workflow
- [ ] 6.3 Demo mit denselben Compose-Dateien deployen (Override-Datei für Produktion, Rate-Limit, Kostendeckel), Link im README und im Lebenslauf
