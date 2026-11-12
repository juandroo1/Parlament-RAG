"""Fake-Datenquelle für Ingest-Tests: liefert die echten Fixtures statt Live-Daten."""

import datetime as dt
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from parlrag.ingest.schemas import BusinessRow, MeetingRow, SessionRow, SubjectRow, TranscriptRow

FIXTURES = Path(__file__).parent / "fixtures" / "odata"
PFAS_DAY = dt.date(2026, 9, 15)


def fixture_rows(name: str) -> list[dict[str, Any]]:
    data = json.loads((FIXTURES / name).read_text(encoding="utf-8"))["d"]
    rows = data["results"] if isinstance(data, dict) else data
    assert isinstance(rows, list)
    return rows


class FixtureSource:
    """Herbstsession 2026; Traktanden nur für Sitzung 5262 (SR, 15.09.2026), Voten nur für
    diesen Tag, Geschäfte nur 25.3906 (DE und FR). Zählt die Aufrufe."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def sessions(self, since: dt.date, until: dt.date) -> list[SessionRow]:
        self.calls.append(("sessions", (since, until)))
        rows = [SessionRow.model_validate(r) for r in fixture_rows("session_legislature52_de.json")]
        return [s for s in rows if s.start_date.date() <= until and s.end_date.date() >= since]

    def meetings(self, session_id: int) -> list[MeetingRow]:
        self.calls.append(("meetings", session_id))
        rows = [MeetingRow.model_validate(r) for r in fixture_rows("meeting_session5215_de.json")]
        return [m for m in rows if m.session_id == session_id]

    def subjects(self, meeting_id: int) -> list[SubjectRow]:
        self.calls.append(("subjects", meeting_id))
        if meeting_id != 5262:
            return []
        return [SubjectRow.model_validate(r) for r in fixture_rows("subject_meeting5262_de.json")]

    def transcripts(self, session_id: int, day: dt.date) -> list[TranscriptRow]:
        self.calls.append(("transcripts", (session_id, day)))
        if session_id != 5215 or day != PFAS_DAY:
            return []
        rows = fixture_rows("transcript_subject82315_de.json")
        # Wie der echte Dienst mit Filter `Type eq 1`.
        return [TranscriptRow.model_validate(r) for r in rows if r["Type"] == 1]

    def businesses(self, ids: Sequence[int], language: str) -> list[BusinessRow]:
        self.calls.append(("businesses", (tuple(ids), language)))
        name = {"DE": "business_20253906_de.json", "FR": "business_20253906_fr.json"}[language]
        rows = [BusinessRow.model_validate(r) for r in fixture_rows(name)]
        return [b for b in rows if b.id in ids]
