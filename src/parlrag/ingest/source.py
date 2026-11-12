"""Datenquelle für den Ingest: alle OData-Abfragen an einem Ort (plan.md, Abschnitt 3).

`Source` ist das Interface, gegen das die Pipeline arbeitet; Tests setzen eine
Fake-Quelle mit Fixtures ein, `ODataSource` fragt den echten Dienst über den
gedrosselten, cachenden `ODataClient` ab.
"""

import datetime as dt
from collections.abc import Sequence
from typing import Protocol

from parlrag.ingest.odata import ODataClient
from parlrag.ingest.schemas import BusinessRow, MeetingRow, SessionRow, SubjectRow, TranscriptRow

VOTUM_TYPE = 1


class Source(Protocol):
    def sessions(self, since: dt.date, until: dt.date) -> list[SessionRow]: ...

    def meetings(self, session_id: int) -> list[MeetingRow]: ...

    def subjects(self, meeting_id: int) -> list[SubjectRow]: ...

    def transcripts(self, session_id: int, day: dt.date) -> list[TranscriptRow]: ...

    def businesses(self, ids: Sequence[int], language: str) -> list[BusinessRow]: ...


class ODataSource:
    """Abfragen gegen ws.parlament.ch; Metadaten immer aus den DE-Zeilen (plan.md, Abschnitt 3)."""

    def __init__(self, client: ODataClient, *, refresh: bool = False) -> None:
        self.client = client
        self.refresh = refresh

    def sessions(self, since: dt.date, until: dt.date) -> list[SessionRow]:
        flt = (
            f"Language eq 'DE' and StartDate le datetime'{until.isoformat()}T23:59:59'"
            f" and EndDate ge datetime'{since.isoformat()}T00:00:00'"
        )
        rows = self.client.iter_rows(
            "Session", filter=flt, orderby="StartDate", refresh=self.refresh
        )
        return [SessionRow.model_validate(row) for row in rows]

    def meetings(self, session_id: int) -> list[MeetingRow]:
        rows = self.client.iter_rows(
            "Meeting",
            filter=f"IdSession eq {session_id} and Language eq 'DE'",
            orderby="Date,Council",
            refresh=self.refresh,
        )
        return [MeetingRow.model_validate(row) for row in rows]

    def subjects(self, meeting_id: int) -> list[SubjectRow]:
        rows = self.client.iter_rows(
            "Subject",
            filter=f"IdMeeting eq {meeting_id} and Language eq 'DE'",
            expand=["SubjectsBusiness"],
            orderby="SortOrder",
            refresh=self.refresh,
        )
        return [SubjectRow.model_validate(row) for row in rows]

    def transcripts(self, session_id: int, day: dt.date) -> list[TranscriptRow]:
        # Der Text ist in allen Sprachzeilen identisch: nur die DE-Zeile laden (Task 0.2).
        flt = (
            f"IdSession eq '{session_id}' and MeetingDate eq '{day:%Y%m%d}'"
            f" and Language eq 'DE' and Type eq {VOTUM_TYPE}"
        )
        rows = self.client.iter_rows("Transcript", filter=flt, refresh=self.refresh)
        return [TranscriptRow.model_validate(row) for row in rows]

    def businesses(self, ids: Sequence[int], language: str) -> list[BusinessRow]:
        if not ids:
            return []
        id_filter = " or ".join(f"ID eq {business_id}" for business_id in ids)
        rows = self.client.iter_rows(
            "Business",
            filter=f"Language eq '{language}' and ({id_filter})",
            refresh=self.refresh,
        )
        return [BusinessRow.model_validate(row) for row in rows]
