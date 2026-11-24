"""Personen mit Voten im Korpus (Spec 003, AK-18.1 und plan.md Abschnitt 6).

Abgeleitet aus `documents`, ohne eigene Tabelle: pro `speaker_name` die Angaben des jüngsten
Votums (Fraktion, Kanton, Rat, Funktion) und die Zahl der Voten. Der Name ist zugleich der Wert
für den Filter `speaker`.
"""

import unicodedata

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Connection, text

# Funktionen im Bundesrat: Mitglied, Bundespräsident/in, Vizepräsident/in (je M/F).
FEDERAL_COUNCIL_FUNCTIONS = frozenset({"BR-M", "BR-F", "BPR-M", "BPR-F", "VPBR-M", "VPBR-F"})

SPEAKERS_SQL = text("""
SELECT DISTINCT ON (speaker_name)
       speaker_name, parl_group, canton, council, speaker_function,
       count(*) OVER (PARTITION BY speaker_name) AS votes
FROM documents
WHERE source_type = 'transcript' AND speaker_name IS NOT NULL
ORDER BY speaker_name, date DESC, sort_order DESC NULLS LAST
""")


class Speaker(BaseModel):
    """Eine Person mit Voten; Angaben aus dem jüngsten Votum."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Wie in den Daten, «Nachname Vorname»; Wert für `speaker`.")
    parl_group: str | None = Field(description="Fraktion, z. B. S, RL; null beim Bundesrat.")
    canton: str | None
    council: str | None = Field(description="NR, SR oder V (Vereinigte Bundesversammlung).")
    federal_council: bool = Field(description="Mitglied des Bundesrats.")
    votes: int = Field(description="Zahl der Voten im Korpus.")


def sort_key(name: str) -> str:
    """Alphabetisch ohne Rücksicht auf Akzente und Gross-/Kleinschreibung («Égerszegi» bei E)."""
    decomposed = unicodedata.normalize("NFKD", name)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def list_speakers(connection: Connection) -> list[Speaker]:
    rows = connection.execute(SPEAKERS_SQL)
    speakers = [
        Speaker(
            name=row.speaker_name,
            parl_group=row.parl_group,
            canton=row.canton,
            council=row.council,
            federal_council=row.speaker_function in FEDERAL_COUNCIL_FUNCTIONS,
            votes=row.votes,
        )
        for row in rows
    ]
    return sorted(speakers, key=lambda speaker: sort_key(speaker.name))
