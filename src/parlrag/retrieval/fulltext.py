"""Volltextsuche über `chunks.tsv` (Entscheidungsprotokoll, Task 2.4).

- Die Sprache der Frage wird an häufigen Funktionswörtern erkannt (DE/FR). Die Frage wird
  mit dieser Konfiguration in Wortstämme zerlegt und gegen alle Chunks gestellt. Ist die
  Sprache nicht erkennbar, wird sie je Chunk-Sprache (`german`/`french`) zerlegt.
  Grund: Deutsche Stoppwörter («und», «der») sind französisch gültige Wortstämme.
- Die Wortstämme werden mit ODER verknüpft und ohne erneutes Stemming als `tsquery`
  verwendet; `ts_rank_cd` sortiert Chunks mit mehr und dichteren Treffern nach oben.
"""

import re
import uuid
from typing import Literal

from sqlalchemy import Connection, text

from parlrag.retrieval.filters import FILTER_SQL, SearchFilters

QueryLanguage = Literal["de", "fr"]
CONFIGS: dict[QueryLanguage, str] = {"de": "german", "fr": "french"}

_FUNCTION_WORDS: dict[QueryLanguage, frozenset[str]] = {
    "de": frozenset(
        [
            "der",
            "die",
            "das",
            "den",
            "dem",
            "des",
            "und",
            "oder",
            "ist",
            "sind",
            "wurde",
            "wurden",
            "wird",
            "werden",
            "im",
            "in",
            "zum",
            "zur",
            "vom",
            "von",
            "mit",
            "für",
            "auf",
            "bei",
            "über",
            "welche",
            "welcher",
            "welches",
            "was",
            "wer",
            "wie",
            "warum",
            "hat",
            "haben",
            "nicht",
            "ein",
            "eine",
            "einen",
            "einem",
            "eines",
        ]
    ),
    "fr": frozenset(
        [
            "le",
            "la",
            "les",
            "l",
            "des",
            "du",
            "de",
            "et",
            "ou",
            "est",
            "sont",
            "été",
            "a",
            "ont",
            "au",
            "aux",
            "dans",
            "pour",
            "sur",
            "par",
            "avec",
            "quel",
            "quelle",
            "quels",
            "quelles",
            "que",
            "qui",
            "quoi",
            "comment",
            "pourquoi",
            "une",
            "un",
            "ne",
            "pas",
            "ce",
            "cette",
        ]
    ),
}


_ALL_FUNCTION_WORDS = _FUNCTION_WORDS["de"] | _FUNCTION_WORDS["fr"]
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def detect_query_language(query: str) -> QueryLanguage | None:
    """Sprache der Frage nach Funktionswörtern; `None`, wenn nicht eindeutig."""
    words = [word.lower() for word in _WORD.findall(query)]
    counts = {lang: sum(word in vocab for word in words) for lang, vocab in _FUNCTION_WORDS.items()}
    if counts["de"] == counts["fr"]:
        return None
    return "de" if counts["de"] > counts["fr"] else "fr"


def strip_function_words(query: str) -> str:
    """Entfernt Funktionswörter beider Sprachen; Postgres-Stoppwortlisten sind lückenhaft."""
    return _WORD.sub(
        lambda match: "" if match.group(0).lower() in _ALL_FUNCTION_WORDS else match.group(0),
        query,
    ).strip()


def _or_query(config_param: str) -> str:
    return (
        "CAST(array_to_string(ARRAY(SELECT quote_literal(lexeme) FROM unnest(tsvector_to_array("
        f"to_tsvector(CAST(:{config_param} AS regconfig), :query))) AS lexeme), ' | ') AS tsquery)"
    )


FULLTEXT_SQL = f"""
WITH q AS (SELECT {_or_query("config_de")} AS de, {_or_query("config_fr")} AS fr)
SELECT c.id,
       ts_rank_cd(c.tsv, CASE c.language WHEN 'de' THEN q.de ELSE q.fr END) AS score
FROM chunks c
JOIN documents d ON d.id = c.document_id
CROSS JOIN q
WHERE ((c.language = 'de' AND c.tsv @@ q.de) OR (c.language = 'fr' AND c.tsv @@ q.fr))
  AND {FILTER_SQL}
ORDER BY score DESC, c.id
LIMIT :limit
"""


def search_fulltext(
    connection: Connection, query: str, filters: SearchFilters, limit: int
) -> list[tuple[uuid.UUID, float]]:
    """(Chunk-ID, Score) in absteigender Reihenfolge; leer, wenn die Frage keine Wortstämme hat."""
    language = detect_query_language(query)
    content = strip_function_words(query)
    if not _WORD.search(content):
        return []
    config_de = CONFIGS[language] if language else CONFIGS["de"]
    config_fr = CONFIGS[language] if language else CONFIGS["fr"]
    rows = connection.execute(
        text(FULLTEXT_SQL),
        {
            "query": content,
            "limit": limit,
            "config_de": config_de,
            "config_fr": config_fr,
            **filters.sql_params(),
        },
    )
    return [(row[0], float(row[1])) for row in rows]
