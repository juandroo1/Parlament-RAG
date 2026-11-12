#!/bin/sh
# Bringt das Datenbankschema auf den neuesten Stand und startet dann den eigentlichen Befehl
# (uvicorn oder z. B. `docker compose run --rm app parlrag ...`).
set -e

python -m parlrag.db.migrate

exec "$@"
