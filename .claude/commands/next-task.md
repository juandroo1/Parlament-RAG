Lies `CLAUDE.md` sowie `specs/001-frag-das-parlament/spec.md`, `plan.md` und `tasks.md`.

Bearbeite den Task $ARGUMENTS. Ist nichts angegeben, nimm den ersten offenen Task in `tasks.md`.

1. Prüfe mit `gh pr list`, ob noch ein Pull Request eines früheren Tasks offen ist. Falls ja: anhalten und melden. Sonst `git checkout main && git pull`, dann Branch `task/<nr>-<kurzname>` anlegen (Ausnahme: Task 0.1, siehe tasks.md).
2. Fasse zusammen, was der Task verlangt und welche Akzeptanzkriterien aus `spec.md` betroffen sind.
3. Schlage einen kurzen Umsetzungsplan vor (Dateien, Tests, Änderungen an Docker oder `.env.example`, offene Punkte) und warte auf meine Bestätigung.
4. Setze den Task um, inklusive Tests. Passe Dockerfile und `docker-compose.yml` im selben Task an, falls nötig.
5. Führe `uv run pytest`, `uv run ruff check .` und `uv run mypy src` aus und behebe Fehler.
6. Prüfe den Container (in Phase 0 erst ab Task 0.3): `docker compose up -d --build`, alle Services healthy, neue Befehle mit `docker compose run --rm app ...` ausführbar.
7. Betrifft der Task Chunking, Retrieval oder Prompts und existiert der Eval-Runner schon: Führe lokal `uv run parlrag eval --suite smoke` aus und zeige die Veränderung.
8. Hake den Task in `tasks.md` ab, aktualisiere README-Quickstart und `.env.example` falls nötig, ergänze bei Abweichungen das Entscheidungsprotokoll in `plan.md`.
9. Committe in sinnvollen Schritten (Conventional Commits, Englisch), pushe den Branch und eröffne mit `gh pr create` einen Pull Request gemäss `CLAUDE.md` (Titel als Conventional Commit mit Task-Nummer). Nicht mergen.
