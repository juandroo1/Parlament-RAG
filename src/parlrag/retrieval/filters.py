"""Filter nach Rat, Zeitraum und Fraktion als SQL-WHERE vor der Suche (AK-4.1 bis AK-4.3).

- Voten: `council`, `date` und `parl_group` des Dokuments.
- Geschäfte: Rat und Zeitraum über `debate_councils` und `debate_dates`, unabhängig
  voneinander geprüft (bekannte Grenze, spec.md AK-4.3). Bei einem Fraktionsfilter fallen
  Geschäfte weg.
"""

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

# Bedingung auf die Tabelle `documents` mit Alias `d`; ungesetzte Filter sind NULL.
FILTER_SQL = """
(
    CAST(:council AS text) IS NULL
    OR (d.source_type = 'transcript' AND d.council = CAST(:council AS text))
    OR (d.source_type = 'business' AND CAST(:council AS text) = ANY(d.debate_councils))
)
AND (
    (CAST(:date_from AS date) IS NULL AND CAST(:date_to AS date) IS NULL)
    OR (d.source_type = 'transcript' AND d.date
        BETWEEN coalesce(CAST(:date_from AS date), DATE '-infinity')
            AND coalesce(CAST(:date_to AS date), DATE 'infinity'))
    OR (d.source_type = 'business' AND EXISTS (
        SELECT 1 FROM unnest(d.debate_dates) AS debate(day)
        WHERE debate.day BETWEEN coalesce(CAST(:date_from AS date), DATE '-infinity')
                             AND coalesce(CAST(:date_to AS date), DATE 'infinity')))
)
AND (
    CAST(:parl_group AS text) IS NULL
    OR (d.source_type = 'transcript' AND d.parl_group = CAST(:parl_group AS text))
)
"""


class SearchFilters(BaseModel):
    """Filter der Suche, alle optional; entspricht `filters` in `POST /ask` (plan.md, Abschn. 8)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    council: Literal["NR", "SR", "V"] | None = None
    date_from: dt.date | None = None
    date_to: dt.date | None = None
    parl_group: str | None = None

    @model_validator(mode="after")
    def _check_range(self) -> "SearchFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from liegt nach date_to")
        return self

    def sql_params(self) -> dict[str, Any]:
        return {
            "council": self.council,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "parl_group": self.parl_group,
        }
