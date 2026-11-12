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

- OData-v3-Endpunkt: `https://ws.parlament.ch/odata.svc/`, ohne API-Key. Das Schema steht unter `$metadata` (Kopie in `tests/fixtures/odata/metadata.xml`).
- Das Schema ist nur teilweise dokumentiert. Deshalb wird nie direkt gegen die Live-API getestet, sondern gegen gespeicherte Fixtures (`tests/fixtures/odata/`, Herkunft im dortigen README).

Verifiziert in Task 0.2 (Stand 2026-11-12, Beispiel: Herbstsession 2026, Ständerat 15.09.2026, Traktandum PFAS):

**Format**
- Mit `$format=json` liefert der Dienst OData-v3-JSON. Eine Collection kommt entweder als `{"d": [...]}` oder als `{"d": {"results": [...], "__count": ..., "__next": ...}}`; der Client muss beide Formen verarbeiten.
- Jede Entität hat den Schlüssel `(ID, Language)` und existiert einmal pro Sprache.
- Int64-Werte (z. B. `Subject.ID`, `Meeting.ID`, `Transcript.ID`, `Transcript.IdSubject`) kommen im JSON als String, Int32-Werte (z. B. `Session.ID`, `Business.ID`) als Zahl. Die Pydantic-Modelle in Task 1.2 wandeln sie um.
- Datumswerte kommen als `/Date(<ms>)/`. Es handelt sich um Schweizer Ortszeit, die als UTC kodiert ist (ein Sitzungsdatum ist z. B. `00:00 UTC`). Sie werden als lokale Zeit ohne Zeitzone übernommen.

**Kette zu den Wortprotokollen**
- `Session.ID` → `Meeting.IdSession` → `Subject.IdMeeting` → `Transcript.IdSubject`.
- `Meeting.Council`: 1 = Nationalrat, 2 = Ständerat, 3 = Vereinigte Bundesversammlung (Kürzel `V`, nicht `VB`).
- Ein Traktandum (`Subject`) kann mehrere Geschäfte umfassen, verknüpft über `SubjectBusiness(IdSubject, BusinessNumber)`; `BusinessNumber` ist die `Business.ID` (z. B. `20253906`), `BusinessShortNumber` die bekannte Nummer (z. B. `25.3906`). Beispiel: Traktandum 82315 behandelt drei Motionen.

**Sprache der Voten**
- Bestätigt: `Transcript.Language` ist nur die Sprache der Bezeichnungen. Der `Text` ist in allen Sprachzeilen identisch und liegt nur in der Originalsprache vor; diese steht in `LanguageOfText` (`DE`, `FR`, `IT` oder leer bei Verfahrenstexten).
- Übersetzt sind nur Bezeichnungen: `CouncilName`, `CantonName`, `ParlGroupName`, `VoteBusinessTitle`. Sprachneutral sind u. a. `ParlGroupAbbreviation` (z. B. `RL`, `S`, `V`, `M-E`), `CantonAbbreviation`, `CouncilId`, `MeetingCouncilAbbreviation`.
- Folge: Transcripts werden nur aus den Zeilen mit `Language eq 'DE'` geladen; die Dokumentsprache ist `LanguageOfText`.

**Arten von Einträgen**
- `Type = 1`: Votum. Darunter auch präsidiale Verfahrensvoten (`LanguageOfText` leer, `DisplaySpeaker = false`, Text beginnt mit «Präsident (Name, Präsident):»).
- `Type = 2`: Verfahrenstext ohne Redner, z. B. Abstimmungsergebnis oder Rückzug.
- Indexiert werden nur Einträge mit `Type = 1` und `LanguageOfText` in `DE` oder `FR`. Italienische Voten (Nicht-Ziel) und Verfahrenstexte fallen weg.

**Metadaten pro Votum** (AK-2.1, AK-4.2)
- Redner: `SpeakerFullName`; Funktion: `SpeakerFunction` (z. B. `Mit-M`/`Mit-F` Mitglied, `P-M` Präsident, `1VP`/`2VP` Vizepräsidium, `BR-M`/`BR-F` Bundesrat).
- Fraktion: `ParlGroupAbbreviation` (sprachneutral); bei Bundesratsmitgliedern leer.
- `CouncilId` ist der Rat des Redners (99 = Bundesrat), nicht der Rat der Sitzung. Der Rat der Sitzung kommt aus `Meeting.Council` bzw. `MeetingCouncilAbbreviation`.
- Datum: `MeetingDate` (Text, `YYYYMMDD`); Reihenfolge: `SortOrder`.

**Textformat**
- Voten: `<pd_text>` mit `<p>`, `<b>`, `<i>` und Platzhaltern `[GZ]`, `[VS]`, `[NB]` (geschütztes Leerzeichen), `[PAGE n]` (Seitenzahl im Amtlichen Bulletin), `[NAM]`.
- Geschäfte: normales HTML mit `<p>`, `<ul>`, `<li>`, `<span>`, `<br>`, `&nbsp;`.

**Geschäfte (Curia Vista)**
- Die Textfelder sind echte Übersetzungen; DE und FR sind getrennte Dokumente.
- Bei einer Motion gefüllt: `Title`, `SubmittedText`, `ReasonText`, `FederalCouncilResponseText`. Weitere Felder (`Description`, `InitialSituation` usw.) sind bei anderen Geschäftsarten zu prüfen (Task 1.2).
- Abkürzungen sind übersetzt (`NR` gegenüber `CN`); Filter verwenden deshalb numerische IDs (`SubmissionCouncil`).
- Datumsfelder: `SubmissionDate`, `BusinessStatusDate`, `FederalCouncilProposalDate`.
- Umfang: Geladen werden nur Geschäfte, die über `SubjectBusiness` mit einem Traktandum im Zeitraum verknüpft sind (spec.md, Abschnitt 5). Seit 2023-12-01 wurden 10'221 Geschäfte eingereicht, die meisten davon nie im Rat debattiert.

**Deep-Links** (AK-2.2)
- Votum im Amtlichen Bulletin: `https://www.parlament.ch/de/ratsbetrieb/amtliches-bulletin/amtliches-bulletin-die-verhandlungen?SubjectId={Subject.ID}#votum{Transcript.SortOrder}`. Das Format stammt aus dem Seitentemplate; die Seite rendert im Browser, der Anker lässt sich per HTTP nicht prüfen.
- Druckansicht eines einzelnen Votums: `https://print.parlament.ch/printview/?contentId={Transcript.ID}`.
- Geschäft: `https://www.parlament.ch/de/ratsbetrieb/suche-curia-vista/geschaeft?AffairId={Business.ID}` (HTTP 200 geprüft). Für französische Dokumente `/fr/` statt `/de/` (nicht separat geprüft).

**Paginierung und Umfang**
- Pro Antwort höchstens 1000 Zeilen. Der Server blättert selbst: Die Antwort enthält einen `__next`-Link mit `$skiptoken`, dem der Client folgt (kein `$skip`). `$inlinecount=allpages` liefert `__count`.
- Kurze Pausen zwischen Requests, Retry mit exponentiellem Backoff.
- Seit 2023-12-01: 41'245 Transcript-Einträge, davon 36'382 mit `Type = 1`; eine ordentliche Session hat rund 4'300 Einträge.

## 4. Datenmodell

```
documents
  id               uuid pk
  source_type      text  -- 'transcript' | 'business'
  source_id        text  -- Transcript.ID bzw. Business.ID
  language         text  -- 'de' | 'fr'; Transcript: LanguageOfText, Business: Sprachversion
  title            text  -- Transcript: Titel des Traktandums; Business: Title
  text             text  -- bereinigt
  speaker_name     text null
  speaker_function text null  -- z. B. 'Mit-M', 'BR-F'
  parl_group       text null  -- ParlGroupAbbreviation, sprachneutral
  canton           text null  -- CantonAbbreviation
  council          text null  -- Transcript: Rat der Sitzung 'NR' | 'SR' | 'V'; Business: null
  date             date       -- Transcript: Sitzungsdatum; Business: Einreichungsdatum (nur Anzeige)
  debate_dates     date[]     -- Business: Daten aller Debatten im Zeitraum (Filter); Transcript: leer
  debate_councils  text[]     -- Business: Räte dieser Debatten (Filter); Transcript: leer
  business_numbers text[]     -- Kurznummern, z. B. {'25.3902','25.3906'}; leer, wenn keine
  session_id       int null
  subject_id       bigint null  -- für den Deep-Link
  sort_order       int null     -- für den Deep-Link (#votum{sort_order})
  url              text
  raw_hash         text  -- für idempotente Ingestion
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

Indizes: GIN auf `chunks.tsv`, HNSW auf `chunks.embedding` (Cosine), B-Tree auf `documents(date, council, parl_group)`, GIN auf `documents.business_numbers`.

## 5. Chunking

- Transcripts: Ein Votum ist die natürliche Einheit. Kurze Voten bleiben ganz, lange werden an Absatzgrenzen in Stücke von etwa 400–600 Tokens mit etwa 15 % Overlap geteilt.
- Vor dem Einbetten erhält jeder Chunk einen Kontext-Header, z. B. `Ständerat · 12.03.2025 · Max Muster (FDP-Liberale Fraktion) · Geschäft 24.123 – Titel`. Gespeichert wird der Chunk ohne Header, eingebettet mit Header.
- Geschäfte: Titel, eingereichter Text und Antwort des Bundesrates werden als getrennte Chunks gespeichert.

## 6. Retrieval

1. Filter (Rat, Zeitraum, Fraktion) als SQL-`WHERE`, angewendet vor der Suche. Voten werden über `date`, `council` und `parl_group` gefiltert, Geschäfte über `debate_dates` und `debate_councils`; bei einem Fraktionsfilter werden Geschäfte ausgeschlossen (AK-4.3).
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
| 2026-11-12 | Transcripts nur aus den Zeilen mit `Language eq 'DE'` laden; Dokumentsprache ist `LanguageOfText`. Indexiert werden nur Einträge mit `Type = 1` und `LanguageOfText` in DE oder FR. (Task 0.2) | Der Text ist in allen Sprachzeilen identisch, sonst entstünden Duplikate. Italienisch ist ein Nicht-Ziel; Verfahrenstexte und Abstimmungsergebnisse sind keine Voten. |
| 2026-11-12 | Datenmodell `documents`: `business_numbers text[]` statt `business_number`; neue Felder `speaker_function`, `canton`, `session_id`, `subject_id`, `sort_order`; Ratskürzel `V` statt `VB`; `parl_group` als sprachneutrale Abkürzung. (Task 0.2) | Ein Traktandum umfasst oft mehrere Geschäfte; `subject_id` und `sort_order` werden für den Deep-Link gebraucht (AK-2.2); Fraktionsnamen sind übersetzt, die Abkürzungen nicht. |
| 2026-11-12 | Paginierung über den `__next`-Link (`$skiptoken`) statt `$top`/`$skip`. (Task 0.2) | Der Server begrenzt auf 1000 Zeilen pro Antwort und blättert selbst. |
| 2026-11-12 | Geschäfte nur laden, wenn sie über `SubjectBusiness` mit einem Traktandum im Zeitraum verknüpft sind. (Task 0.2) | Entspricht spec.md, Abschnitt 5 («sofern im Zeitraum behandelt»); die meisten der rund 10'000 eingereichten Geschäfte wurden nie debattiert. |
| 2026-11-12 | Filter bei Geschäften (AK-4.3): Zeitraum und Rat beziehen sich auf die Debatten des Geschäfts (`debate_dates`, `debate_councils`), nicht auf Einreichungsdatum und Einreichungsrat. Bei einem Fraktionsfilter fallen Geschäfte weg. Zeitraum und Rat werden unabhängig geprüft; keine eigene Tabelle pro Debatte. Entscheid Sandro. | Eine Nutzerin, die nach «Ständerat, 2025» filtert, will wissen, was dort und dann behandelt wurde. Geschäftsdokumente enthalten auch die Antwort des Bundesrates und gehören keiner Fraktion. Der Grenzfall bei der Kombination von Zeitraum und Rat ist selten und wird als bekannte Grenze dokumentiert. |
| 2026-11-12 | DB-Konfiguration über `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT` statt `DATABASE_URL`; `Settings` baut die URL daraus. Compose setzt für `app` nur `POSTGRES_HOST=db`; `db` erhält die Zugangsdaten per Interpolation aus `.env`. (Task 0.3) | Lokal ist der Host `localhost`, im Container `db`; eine einzige URL in `.env` passt nicht für beide. So steht kein Passwort in `docker-compose.yml`, und `db` sieht den Anthropic-Key nicht. |
| 2026-11-12 | Volumes `hf-cache` und `./data/raw` werden erst in den Tasks angelegt, die sie brauchen (2.2 bzw. 1.1). In Task 0.3 nur `pgdata`. | Regel «Dockerfile und Compose im selben Task anpassen»; keine ungenutzten Volumes. |
| 2026-11-12 | `GET /health` prüft in Task 0.3 nur, ob die App läuft; der Datenbank-Check kommt in Task 0.4 mit dem DB-Treiber. | Noch kein Datenbanktreiber vorhanden. |
| 2026-11-12 | Schema als SQLAlchemy-Modelle (`parlrag.db.models`) plus Alembic-Migration im Paket (`parlrag/db/migrations`); ein Test vergleicht Modelle und Migration. Treiber: psycopg 3. (Task 0.4) | Ingest und Retrieval brauchen die Modelle; die Migration muss im Image ohne `src/` verfügbar sein; der Vergleichstest verhindert Drift. |
| 2026-11-12 | `chunks.tsv` ist eine generierte Spalte: `to_tsvector('german'` bzw. `'french'` je nach `language`, `text)`, ohne Kontext-Header. (Task 0.4) | Postgres hält sie ohne App-Code aktuell. Ob Header-Felder in die Volltextsuche gehören, wird per Eval entschieden (Task 3.3); eine Änderung ist eine einfache Migration. |
| 2026-11-12 | CHECK-Constraints für `source_type`, `language` und `council`. (Task 0.4) | Ungültige Werte fallen beim Ingest sofort auf statt erst beim Filtern. |
| 2026-11-12 | Migrationen laufen über ein Entrypoint-Skript bei jedem Start des `app`-Containers, also auch bei `docker compose run --rm app …`. (Task 0.4) | CLI-Befehle im Container finden immer ein aktuelles Schema vor. |
| 2026-11-12 | Schema-Tests laufen gegen echtes Postgres in einer eigenen Datenbank `parlrag_test` (Marker `db`, übersprungen ohne erreichbare DB). Die eigene Datenbank gilt nicht als «externe API» im Sinne der Test-Regel. (Task 0.4) | Schema, Indizes, generierte Spalten und Constraints lassen sich ohne echtes Postgres nicht sinnvoll prüfen. |
| 2026-11-12 | Standardwert `POSTGRES_HOST=127.0.0.1` statt `localhost`; alle Datenbankverbindungen (App, Migrationen, Tests) mit `connect_timeout`. (Task 0.4) | Unter Windows löst `localhost` zuerst zu `::1` auf; Docker lauscht nur auf `127.0.0.1`, und psycopg wartete ohne Timeout unbegrenzt auf den IPv6-Versuch (Testlauf hing). |
| 2026-11-12 | CI-Trigger: `push` nur auf `main`, dazu jeder Pull Request (statt jedem Push auf jeden Branch). Actions auf Commit-SHA gepinnt. Die Wegwerf-Datenbank der CI hat feste Zugangsdaten im Workflow. DB-Tests sind in der CI Pflicht (`PARLRAG_REQUIRE_DB=1`). (Task 0.5) | Jeder PR-Stand wird genau einmal geprüft, ohne doppelte Läufe. SHAs lassen sich nicht nachträglich verschieben (Supply-Chain-Schutz). Die CI-Datenbank existiert nur während des Laufs. Ohne Pflicht würden die DB-Tests bei einem Konfigurationsfehler still übersprungen. |
| 2026-11-12 | HTTP-Client `httpx2` (statt `httpx`) als Laufzeit-Abhängigkeit. (Task 1.1) | Bereits im Lockfile und von Starlette für den TestClient verlangt; so bleibt es bei einer HTTP-Bibliothek. |
| 2026-11-12 | OData-Rohdaten-Cache ohne Ablaufdatum: Antwort byte-genau in `data/raw/odata/<Entität>/<sha256(URL)>.json` plus `.meta.json` (URL, Abrufzeit); nur erfolgreiche Antworten; `refresh=True` umgeht den Cache. (Task 1.1) | Abgeschlossene Sessions ändern sich praktisch nicht; `$skiptoken`-URLs sind stabil. Byte-genaue Ablage wie bei den Fixtures. Für die laufende Session folgt `--refresh` in der CLI (Task 1.3). |
| 2026-11-12 | Evals laufen nur lokal mit uv, nicht im Container. | Im Image gibt es kein `.git` (kein Git-SHA), und die Ergebnisse in `evals/results/` sollen direkt committet werden. |
