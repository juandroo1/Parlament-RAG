# Frag das Parlament

RAG-Anwendung, die Fragen zu Debatten und Geschäften des Schweizer Bundesparlaments beantwortet, auf Deutsch und Französisch. Grundlage sind das Amtliche Bulletin (Wortprotokolle) und Curia Vista (Geschäfte). Jede Aussage ist mit einer überprüfbaren Quelle auf parlament.ch belegt. Die Qualität wird mit einem reproduzierbaren Eval-Set gemessen.

> **Status:** in Entwicklung. Aktuell stehen das Projektgerüst und der Docker-Stack mit Health-Endpoint; Ingestion, Retrieval und Generierung folgen gemäss [`tasks.md`](specs/001-frag-das-parlament/tasks.md).

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

Die Ports sind nur lokal erreichbar: API auf `127.0.0.1:8000`, Datenbank auf `127.0.0.1:5432`. Läuft auf dem Rechner bereits ein anderes Postgres auf Port 5432, in `.env` z. B. `POSTGRES_PORT=5433` setzen.

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
