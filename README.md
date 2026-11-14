# Frag das Parlament

[![CI](https://github.com/juandroo1/Parlament-RAG/actions/workflows/ci.yml/badge.svg)](https://github.com/juandroo1/Parlament-RAG/actions/workflows/ci.yml)

RAG-Anwendung, die Fragen zu Debatten und Geschäften des Schweizer Bundesparlaments beantwortet, auf Deutsch und Französisch. Grundlage sind das Amtliche Bulletin (Wortprotokolle) und Curia Vista (Geschäfte). Jede Aussage ist mit einer überprüfbaren Quelle auf parlament.ch belegt. Die Qualität wird mit einem reproduzierbaren Eval-Set gemessen.

> **Status:** in Entwicklung. Aktuell stehen der Docker-Stack mit CI, Ingestion, Indexierung und hybride Suche über den ganzen Korpus; Generierung, Evals, API und UI folgen gemäss [`tasks.md`](specs/001-frag-das-parlament/tasks.md).

## Quickstart mit Docker

Voraussetzungen: Docker mit Docker Compose und Git.

```bash
git clone https://github.com/juandroo1/Parlament-RAG.git
cd Parlament-RAG
cp .env.example .env              # Werte eintragen
docker compose up -d --build      # Datenbank (Postgres + pgvector) und API starten
docker compose ps                 # beide Services sollten "healthy" sein
curl http://127.0.0.1:8000/health # {"status":"ok","database":"ok"}
docker compose down               # stoppen (Daten bleiben im Volume)
```

Beim Start von `app` (und bei jedem `docker compose run --rm app ...`) bringt ein Entrypoint das Datenbankschema per Alembic auf den neuesten Stand.

### Daten laden

```bash
docker compose run --rm app parlrag ingest --since 2026-09-15 --until 2026-09-15   # ein Sitzungstag
docker compose run --rm app parlrag ingest                                         # ab 2023-12-01 bis heute
docker compose run --rm app parlrag ingest --lang fr --refresh                     # nur FR, Cache umgehen
```

Der Ingest ist idempotent: Ein zweiter Lauf ändert nichts, geänderte Inhalte werden erkannt und aktualisiert. Pro Session wird committet, ein abgebrochener Lauf kann einfach neu gestartet werden.

```bash
docker compose run --rm app parlrag stats                    # Umfang, Textlängen, Verteilung, Qualität
docker compose run --rm app parlrag stats --session-id 5215  # nur eine Session
```

Beispiel Herbstsession 2026: 2'427 Voten (1'737 DE, 690 FR) und 853 Geschäfte je Sprache, geladen in 105 Sekunden.

### Indexieren

```bash
docker compose run --rm app parlrag index --session-id 5215 --limit 40   # Test: 40 Dokumente
docker compose run --rm app parlrag index --session-id 5215              # eine Session (rund 2 Stunden)
docker compose run --rm app parlrag index                                # alles Offene
```

`parlrag index` chunkt neue oder geänderte Dokumente, bettet sie ein und speichert die Chunks mit Vektor. Es ist inkrementell und kann jederzeit abgebrochen und neu gestartet werden (Commit alle 32 Dokumente). Ändert sich eine Einstellung wie `CHUNK_TARGET_TOKENS` oder `INDEX_CONTEXT_HEADER`, indexiert der nächste Lauf die betroffenen Dokumente neu.

### Korpus-Stand

Der Korpus für die Evals ist auf den **Stichtag 2026-10-02** eingefroren (Ende der Herbstsession 2026): 15 Sessions seit der Wintersession 2023, 42'515 Dokumente (26'401 Voten, 8'057 Geschäfte je Sprache) und 102'891 Chunks. Experimente laufen auf dem Teilkorpus Herbstsession 2026 (`--session-id 5215`). Den gleichen Stand erzeugen:

```bash
docker compose run --rm app parlrag ingest --since 2023-12-01 --until 2026-10-02   # rund 20 Minuten
```

Der volle Index dauert auf der CPU rund 17 Stunden (1,7 Chunks/s), die Datenbank braucht danach 1,7 GB. Am besten läuft er losgelöst im Hintergrund, zuerst der Teilkorpus, dann der Rest:

```bash
docker compose run -d --name parlrag-index app sh -c "parlrag index --session-id 5215 && parlrag index"
docker logs -f parlrag-index     # Fortschritt
docker stop parlrag-index        # anhalten; mit demselben Befehl fortsetzen (vorher docker rm parlrag-index)
```

Laufzeiten und Grössen im Detail: [`plan.md`, Abschnitt 3](specs/001-frag-das-parlament/plan.md).

### Suchen (nur Retrieval)

```bash
docker compose run --rm app parlrag search "Was sagte der Bundesrat zu den PFAS-Grenzwerten?"
docker compose run --rm app parlrag search "PFAS" --mode fulltext --council SR --top 5
docker compose run --rm app parlrag search "PFAS" --parl-group RL --date-from 2026-09-01 --date-to 2026-09-30
docker compose run --rm app parlrag search "PFAS" --json
```

Kombiniert Volltext- und Vektorsuche mit Reciprocal Rank Fusion (`--mode hybrid`, Standard) oder nutzt nur eine davon (`fulltext`, `vector`). Filter wirken vor der Suche. Jeder Treffer zeigt die Dokument-ID im Goldset-Format (`transcript:418982`), die Scores, Redner und Fraktion bzw. Geschäftsnummer, Rat, Datum, einen Ausschnitt und den Link auf parlament.ch.

Das Embedding-Modell [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) (MIT-Lizenz) läuft lokal auf der CPU. Es wird beim ersten Gebrauch heruntergeladen (rund 4 GB im Docker-Volume `hf-cache`) und nicht ins Image gebacken. Beim Einbetten braucht der Container rund 4 GB Arbeitsspeicher.

Antworten des OData-Dienstes werden roh in `./data/raw/` zwischengespeichert (nicht im Repo). Jede Abfrage geht damit nur einmal an den Dienst; Requests sind gedrosselt (Standard: höchstens einer pro Sekunde) und werden bei Fehlern mit Backoff wiederholt.

Die Ports sind nur lokal erreichbar: API auf `127.0.0.1:8000`, Datenbank auf `127.0.0.1:5432`. Läuft auf dem Rechner bereits ein anderes Postgres auf Port 5432, in `.env` z. B. `POSTGRES_PORT=5433` setzen.

## Evals

Das Goldset [`evals/datasets/golden.jsonl`](evals/datasets/golden.jsonl) enthält 33 Fragen mit den erwarteten Quellen (Goldset v1): 20 beantwortbare auf Deutsch, 5 auf Französisch, 5 unbeantwortbare und 3 wertende, davon 5 sprachübergreifend und 19 auf den Teilkorpus Herbstsession 2026. Claude hat sie aus dem Korpus vorgeschlagen, Sandro hat jede Frage geprüft. Schema, Tags und Regeln stehen in [`evals/datasets/README.md`](evals/datasets/README.md). Der Eval-Runner folgt in Task 3.2.

## Lokale Entwicklung mit uv

Voraussetzung: [uv](https://docs.astral.sh/uv/). Python 3.12 installiert uv bei Bedarf selbst. Die Datenbank läuft auch dann im Container.

```bash
uv sync                           # Abhängigkeiten installieren
docker compose up -d db           # nur die Datenbank
uv run alembic upgrade head       # Schema migrieren
uv run pytest                     # Tests (DB-Tests nutzen eine eigene Datenbank parlrag_test)
uv run ruff check . && uv run ruff format --check .
uv run mypy src
uv run uvicorn parlrag.api.main:app --reload   # API lokal
```

## Datenquelle und Lizenz

- Daten: Open Data der Parlamentsdienste der Bundesversammlung über den OData-Dienst [ws.parlament.ch](https://ws.parlament.ch/odata.svc/) (Amtliches Bulletin, Curia Vista). Die Nutzungsbedingungen für eine öffentliche Demo werden noch geprüft (siehe offene Fragen in der Spec).
- Code: [MIT-Lizenz](LICENSE).

## Arbeitsweise

Das Projekt folgt Spec-driven Development. Anforderungen, Architektur und Umsetzungsschritte liegen in [`specs/001-frag-das-parlament/`](specs/001-frag-das-parlament/):

- [`spec.md`](specs/001-frag-das-parlament/spec.md): Was und Warum, Akzeptanzkriterien, Qualitätsziele
- [`plan.md`](specs/001-frag-das-parlament/plan.md): Architektur, Stack, Datenmodell, Entscheidungsprotokoll
- [`tasks.md`](specs/001-frag-das-parlament/tasks.md): Umsetzungsschritte
