# CLAUDE.md – Frag das Parlament

## Projekt

RAG-Anwendung, die Fragen zu Debatten und Geschäften des Schweizer Bundesparlaments beantwortet, gestützt auf das Amtliche Bulletin und Curia Vista, mit überprüfbaren Quellenangaben. Portfolio-Projekt: Die Qualität wird mit Evals gemessen, nicht nach Gefühl beurteilt.

## Arbeitsweise: Spec-driven Development

Die Quelle der Wahrheit liegt in `specs/001-frag-das-parlament/`:

- `spec.md` beschreibt das Was und Warum: Anforderungen, Akzeptanzkriterien, Nicht-Ziele.
- `plan.md` beschreibt das Wie: Architektur, Stack, Datenmodell, Entscheidungsprotokoll.
- `tasks.md` enthält die Umsetzungsschritte mit Checkboxen.

Regeln:

1. Vor jeder Aufgabe `spec.md`, `plan.md` und den betroffenen Task in `tasks.md` lesen.
2. Immer nur einen Task bearbeiten. Danach die Checkbox abhaken und in zwei, drei Sätzen zusammenfassen, was gemacht wurde.
3. Wenn eine Anforderung unklar ist oder der Plan nicht aufgeht: anhalten und nachfragen. Nie stillschweigend vom Plan abweichen. Eine Abweichung wird zuerst im Entscheidungsprotokoll von `plan.md` festgehalten und erst danach umgesetzt.
4. Nichts bauen, was nicht in `spec.md` steht. Ideen für später kommen in `spec.md` unter «Offene Fragen».
5. Zu jedem Task gehören Tests, die seine Akzeptanzkriterien prüfen.

## Befehle

Docker ist die Referenzumgebung. Was dort nicht läuft, gilt als nicht fertig.

```bash
cp .env.example .env                                   # einmalig, Werte eintragen
docker compose up -d --build                           # ganzer Stack (db, app, ab Phase 5 web)
docker compose ps                                      # Status inkl. Healthchecks
docker compose logs -f app                             # Logs
docker compose run --rm app parlrag ingest --since 2023-12-01
docker compose run --rm app parlrag index
docker compose run --rm app parlrag search "Frage"
docker compose run --rm app parlrag ask "Frage"
docker compose down                                    # stoppen (Daten bleiben im Volume)
```

Für schnelle Iterationen ist die lokale Entwicklung mit uv erlaubt. Die Datenbank läuft auch dann im Container:

```bash
uv sync
docker compose up -d db
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy src
```

Evals laufen nur lokal mit uv, nicht im Container: So stehen der Git-SHA zur Verfügung und die Ergebnisse landen direkt in `evals/results/`. Die Datenbank läuft dabei im Container.

```bash
uv run parlrag eval --suite smoke                      # schnelle Evals (~15 Fragen)
uv run parlrag eval --suite full                       # alle Evals
```

## Docker

- Services in `docker-compose.yml`:
  - `db`: Image `pgvector/pgvector:pg16`, Healthcheck mit `pg_isready`, Volume `pgdata`.
  - `app`: ein Image für API und CLI. Startet erst, wenn `db` healthy ist (`depends_on` mit `condition: service_healthy`). Führt beim Start `alembic upgrade head` aus und startet danach uvicorn. Healthcheck auf `GET /health`.
  - `web` (ab Phase 5): baut die React-App und liefert sie über nginx aus, `/api` wird an `app` weitergeleitet.
- Dockerfile: Multi-Stage-Build auf `python:3.12-slim` mit uv. `uv sync --frozen --no-dev` im Runtime-Stage, Ausführung als Non-Root-User, ohne Build-Tools im finalen Image.
- Konfiguration nur über `.env` (`env_file`). Keine Secrets im Image und keine in `docker-compose.yml`.
- Volumes: `pgdata` für die Datenbank, `hf-cache` für das Embedding-Modell (wird nicht ins Image gebacken), Bind-Mount `./data/raw` für den Rohdaten-Cache.
- `.dockerignore` hält das Image klein: `.git`, `.venv`, `data/`, `node_modules`, `__pycache__`, `.env`.
- Neue Abhängigkeit, neuer Befehl oder neuer Service: Dockerfile und `docker-compose.yml` im selben Task anpassen, nicht später.
- Ports nur auf `127.0.0.1` binden, ausser beim Deployment.

## Git

- `main` ist jederzeit lauffähig und durch Branch Protection geschützt. Nie direkt auf `main` committen, nie force-push auf `main`.
- Ein neuer Task beginnt erst, wenn der Pull Request des vorherigen Tasks gemergt ist. Ist er noch offen: anhalten und melden.
- Vor jedem Task: `git checkout main && git pull`, dann einen Branch `task/<nr>-<kurzname>` anlegen, z. B. `task/1.1-odata-client`.
- Kleine, in sich geschlossene Commits nach Conventional Commits (`feat:`, `fix:`, `test:`, `eval:`, `docs:`, `refactor:`, `chore:`, `ci:`). Commit-Messages auf Englisch.
- Vor jedem Commit `git status` und `git diff --staged` prüfen. Nie committen: `.env`, Secrets, `data/`, Modelldateien, `.venv`, `node_modules`.
- Eval-Ergebnisse in `evals/results/` werden committet: Sie sind die Historie für das README.
- Ist der Task fertig (Definition of Done): Branch pushen und mit `gh pr create` einen Pull Request eröffnen. Gemergt wird per Squash-Merge, deshalb ist der Titel ein Conventional Commit mit Task-Nummer, z. B. `feat: 1.1 OData client`. Beschreibung: was umgesetzt wurde, wie es getestet wurde, Eval-Ergebnis falls relevant, Abweichungen vom Plan.
- Gemergt wird erst nach grüner CI, und zwar von Sandro, nicht von Claude.
- Ist `gh` nicht verfügbar oder schlägt der Push fehl: anhalten und melden, nicht improvisieren.

## Projektstruktur

```
src/parlrag/
  ingest/        OData-Client, Mapping, Textbereinigung
  index/         Chunker, Indexierung
  embeddings/    Interface + Implementierungen
  retrieval/     Volltext, Vektor, RRF, Filter
  llm/           Interface + Anthropic-Implementierung, Usage/Kosten
  generation/    Antwort-Pipeline, Zitatvalidierung
  prompts/       Prompts als .md-Dateien
  api/           FastAPI
  cli.py         Typer-CLI
evals/
  datasets/      golden.jsonl
  results/       Ergebnisse pro Lauf
tests/
  fixtures/      echte OData-Antworten als JSON
specs/001-frag-das-parlament/
web/             React-UI (Phase 5)
Dockerfile
docker-compose.yml
.github/workflows/ci.yml
```

## Code-Konventionen

- Python 3.12 mit vollständigen Type Hints. Pydantic v2 für alle Daten an Systemgrenzen (OData, API, LLM-Ausgabe).
- Konfiguration nur über Umgebungsvariablen mit pydantic-settings. Eine Vorlage mit allen Variablen liegt in `.env.example` und wird bei jeder neuen Variable nachgeführt.
- LLM- und Embedding-Aufrufe laufen nur über die Interfaces in `llm/` und `embeddings/`, nie direkt aus der Logik.
- Prompts liegen als Dateien in `prompts/`. Jede Prompt-Änderung braucht einen Eval-Lauf zum Vergleich.
- Tests mocken externe APIs und verursachen nie Kosten. Evals sind keine Tests und laufen separat.

## CI (GitHub Actions)

Bei jedem Push und Pull Request:

1. ruff, mypy, pytest.
2. `docker compose build`.
3. Smoke-Test: `docker compose up -d`, warten bis `app` healthy ist, `GET /health` muss 200 liefern, danach `docker compose down -v`.

Evals laufen nicht in der CI, weil sie API-Kosten verursachen.

## Leitplanken

- Antworten nur aus gefundenen Quellen. Reichen die Quellen nicht, sagt das System das klar.
- Politisch neutral: Das System gibt wieder, was gesagt wurde. Es bewertet keine Personen, Parteien oder Vorlagen.
- Nur öffentliche Open-Data-Quellen. Kein Code, keine Daten und kein internes Wissen aus beruflichen Projekten.
- Datenquelle und Lizenz im README und in der UI nennen.
- Den OData-Dienst schonen: Rohdaten lokal cachen, Requests drosseln, Ingestion idempotent halten.

## Definition of Done

Ein Task ist erst fertig, wenn alle Punkte erfüllt sind (für Phase 0 gilt die reduzierte Fassung in `tasks.md`):

- Tests grün, ruff und mypy sauber.
- Akzeptanzkriterien des Tasks erfüllt.
- `docker compose up -d --build` startet ohne Fehler, alle Services sind healthy.
- Neue Funktionen sind im Container ausführbar (`docker compose run --rm app ...`). Ausnahme: Evals laufen nur lokal mit uv.
- Bei Änderungen an Chunking, Retrieval oder Prompts: `uv run parlrag eval --suite smoke` ausgeführt, Ergebnis in der PR-Beschreibung.
- `README.md` (Quickstart) und `.env.example` sind aktuell.
- `tasks.md` abgehakt, Abweichungen im Entscheidungsprotokoll.
- Branch gepusht, Pull Request eröffnet, CI grün.
