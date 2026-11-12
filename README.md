# Frag das Parlament

RAG-Anwendung, die Fragen zu Debatten und Geschäften des Schweizer Bundesparlaments beantwortet, auf Deutsch und Französisch. Grundlage sind das Amtliche Bulletin (Wortprotokolle) und Curia Vista (Geschäfte). Jede Aussage ist mit einer überprüfbaren Quelle auf parlament.ch belegt. Die Qualität wird mit einem reproduzierbaren Eval-Set gemessen.

> **Status:** in Entwicklung. Aktuell steht das Projektgerüst; Ingestion, Retrieval und Generierung folgen gemäss [`tasks.md`](specs/001-frag-das-parlament/tasks.md).

## Quickstart (lokale Entwicklung)

Voraussetzungen: [uv](https://docs.astral.sh/uv/) und Git. Python 3.12 installiert uv bei Bedarf selbst.

```bash
git clone https://github.com/juandroo1/Parlament-RAG.git
cd Parlament-RAG
cp .env.example .env        # Werte eintragen
uv sync                     # Abhängigkeiten installieren
uv run pytest               # Tests
uv run ruff check . && uv run ruff format --check .
uv run mypy src
```

Der Start mit Docker Compose (Datenbank und API) folgt mit Task 0.3.

## Datenquelle und Lizenz

- Daten: Open Data der Parlamentsdienste der Bundesversammlung über den OData-Dienst [ws.parlament.ch](https://ws.parlament.ch/odata.svc/) (Amtliches Bulletin, Curia Vista). Die Nutzungsbedingungen für eine öffentliche Demo werden noch geprüft (siehe offene Fragen in der Spec).
- Code: [MIT-Lizenz](LICENSE).

## Arbeitsweise

Das Projekt folgt Spec-driven Development. Anforderungen, Architektur und Umsetzungsschritte liegen in [`specs/001-frag-das-parlament/`](specs/001-frag-das-parlament/):

- [`spec.md`](specs/001-frag-das-parlament/spec.md): Was und Warum, Akzeptanzkriterien, Qualitätsziele
- [`plan.md`](specs/001-frag-das-parlament/plan.md): Architektur, Stack, Datenmodell, Entscheidungsprotokoll
- [`tasks.md`](specs/001-frag-das-parlament/tasks.md): Umsetzungsschritte
