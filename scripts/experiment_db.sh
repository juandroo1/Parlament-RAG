#!/usr/bin/env bash
# Experiment-Datenbank mit dem Teilkorpus anlegen (Task 6.1b, plan.md Abschnitt 9).
#
#   scripts/experiment_db.sh <name> [documents|chunks]
#
# Legt im laufenden Service `db` die Datenbank <name> an (muss mit parlrag_exp_ beginnen),
# bringt das Schema auf den aktuellen Stand und kopiert aus der Hauptdatenbank die Dokumente
# der Session SESSION_ID (Standard 5215, Herbstsession 2026) samt der dort debattierten
# Geschäfte, also dieselbe Abgrenzung wie `parlrag index --session-id`. Mit `chunks` kommen
# auch deren Chunks samt Embeddings mit (Variante wie im Hauptindex, ohne neu zu rechnen).
# Die Hauptdatenbank wird nur gelesen. Aufruf aus dem Repo-Verzeichnis, z. B. mit Git Bash.
set -euo pipefail

target=${1:?Name der Experiment-Datenbank, z. B. parlrag_exp_base}
what=${2:-documents}
session=${SESSION_ID:-5215}
source_db=${SOURCE_DB:-parlrag}
user=${POSTGRES_USER:-parlrag}

if [[ ! $target =~ ^parlrag_exp_[a-z0-9_]+$ ]]; then
    echo "Der Name muss mit parlrag_exp_ beginnen (nur a-z, 0-9, _)." >&2
    exit 1
fi
if [[ $what != documents && $what != chunks ]]; then
    echo "Zweites Argument: documents oder chunks." >&2
    exit 1
fi
if [[ ! $session =~ ^[0-9]+$ ]]; then
    echo "SESSION_ID muss eine Zahl sein." >&2
    exit 1
fi

scope="WITH session_days AS (
    SELECT min(date) AS first_day, max(date) AS last_day FROM documents
    WHERE source_type = 'transcript' AND session_id = $session),
scope AS (
    SELECT d.* FROM documents d
    WHERE (d.source_type = 'transcript' AND d.session_id = $session)
       OR (d.source_type = 'business' AND EXISTS (
            SELECT 1 FROM unnest(d.debate_dates) AS debate(day), session_days s
            WHERE debate.day BETWEEN s.first_day AND s.last_day)))"
columns="id, document_id, chunk_index, language, text, token_count, embedding, metadata"

# Beide psql laufen im Container, die Daten verlassen ihn nicht. \copy muss auf einer Zeile stehen.
copy() {
    local query
    query=$(echo "$1" | tr '\n' ' ')
    docker compose exec -T db sh -c \
        "psql -U $user -d $source_db -v ON_ERROR_STOP=1 -c \"\\copy ($query) TO STDOUT\" \
         | psql -U $user -d $target -v ON_ERROR_STOP=1 -c \"\\copy $2 FROM STDIN\""
}

echo "Lege $target an und migriere das Schema ..."
docker compose exec -T db createdb -U "$user" "$target"
docker compose run --rm --no-deps -e POSTGRES_DB="$target" app true

echo "Kopiere die Dokumente der Session $session ..."
copy "$scope SELECT * FROM scope" "documents"
if [[ $what == chunks ]]; then
    echo "Kopiere die Chunks ..."
    copy "$scope SELECT $(echo "$columns" | sed 's/[a-z_]\+/c.&/g') FROM chunks c JOIN scope s ON s.id = c.document_id" \
        "chunks ($columns)"
fi
docker compose exec -T db psql -U "$user" -d "$target" -c "ANALYZE" -c \
    "SELECT (SELECT count(*) FROM documents) AS dokumente, (SELECT count(*) FROM chunks) AS chunks"
