#!/usr/bin/env bash
# Datenbank für die Demo übertragen (Task 6.3a), statt auf dem Server rund 17 Stunden neu zu
# indexieren. Läuft über den Service `db`, die Daten verlassen nur als Dump-Datei den Container.
#
#   scripts/db_transfer.sh dump [datei]      lokal: Dump nach data/parlrag.dump (Standard)
#   scripts/db_transfer.sh restore [datei]   Server: Dump einspielen (nur db muss laufen)
#
# restore verweigert, wenn die Datenbank schon Dokumente enthält; mit FORCE=1 wird sie ersetzt.
# Auf dem Server gilt die Produktion, wenn in .env COMPOSE_FILE gesetzt ist (docs/deployment.md).
set -euo pipefail
export MSYS_NO_PATHCONV=1 # Git Bash unter Windows: Pfade im Container nicht umschreiben

action=${1:?Aktion fehlt: dump oder restore}
file=${2:-data/parlrag.dump}
user=${POSTGRES_USER:-parlrag}
database=${POSTGRES_DB:-parlrag}
inside=/tmp/parlrag.dump

db() { docker compose exec -T db "$@"; }

case $action in
dump)
    echo "Erstelle Dump von $database ..."
    db pg_dump -U "$user" -d "$database" --format=custom --no-owner --file="$inside"
    mkdir -p "$(dirname "$file")"
    docker compose cp "db:$inside" "$file"
    db rm -f "$inside"
    ls -lh "$file"
    ;;
restore)
    [[ -f $file ]] || { echo "Datei $file fehlt." >&2; exit 1; }
    documents=$(db psql -U "$user" -d "$database" -tAc \
        "SELECT count(*) FROM documents" 2>/dev/null || echo 0)
    if [[ ${documents:-0} != 0 && ${FORCE:-0} != 1 ]]; then
        echo "Die Datenbank enthält schon $documents Dokumente; mit FORCE=1 ersetzen." >&2
        exit 1
    fi
    echo "Spiele $file in $database ein ..."
    docker compose cp "$file" "db:$inside"
    db pg_restore -U "$user" -d "$database" --clean --if-exists --no-owner --jobs=2 "$inside"
    db rm -f "$inside"
    db psql -U "$user" -d "$database" -c "ANALYZE" -c \
        "SELECT (SELECT count(*) FROM documents) AS dokumente, (SELECT count(*) FROM chunks) AS chunks"
    ;;
*)
    echo "Unbekannte Aktion $action: dump oder restore." >&2
    exit 1
    ;;
esac
