"""Ingest-Ablauf: Quelle → Mapping → `documents` (Task 1.3).

Pro Session:
1. Sitzungen im Zeitraum (inklusive `since` und `until`, bezogen auf das Sitzungsdatum).
2. Traktanden pro Sitzung; daraus Kontext der Voten und Debatten der Geschäfte.
3. Voten pro Sitzungstag (nur `Type = 1`), abgebildet mit `map_transcript`.
4. Geschäfte in Paketen pro Sprache, abgebildet mit `map_business`.
5. Upsert und Commit; ein abgebrochener Lauf verliert keine fertige Session.
"""

import datetime as dt
import logging
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from itertools import batched

from sqlalchemy.orm import Session

from parlrag.ingest.mapping import (
    Debate,
    DocumentData,
    Language,
    SubjectInfo,
    map_business,
    map_transcript,
)
from parlrag.ingest.schemas import SessionRow
from parlrag.ingest.source import Source
from parlrag.ingest.store import UpsertResult, upsert_documents

logger = logging.getLogger(__name__)

BUSINESS_BATCH_SIZE = 40
ODATA_LANGUAGE: dict[Language, str] = {"de": "DE", "fr": "FR"}


@dataclass
class SessionBatch:
    session: SessionRow
    documents: list[DocumentData]
    meetings: int = 0
    subjects: int = 0
    transcripts: int = 0
    skipped_transcripts: int = 0
    businesses: int = 0


@dataclass
class IngestStats:
    sessions: int = 0
    meetings: int = 0
    subjects: int = 0
    transcripts: int = 0
    skipped_transcripts: int = 0
    businesses: int = 0
    documents: int = 0
    stored: UpsertResult = field(default_factory=UpsertResult)

    def add(self, batch: SessionBatch, stored: UpsertResult) -> None:
        self.sessions += 1
        self.meetings += batch.meetings
        self.subjects += batch.subjects
        self.transcripts += batch.transcripts
        self.skipped_transcripts += batch.skipped_transcripts
        self.businesses += batch.businesses
        self.documents += len(batch.documents)
        self.stored += stored


def collect_session(
    source: Source,
    session: SessionRow,
    since: dt.date,
    until: dt.date,
    languages: frozenset[Language],
) -> SessionBatch:
    """Alle Dokumente einer Session im Zeitraum, ohne Datenbankzugriff."""
    batch = SessionBatch(session=session, documents=[])
    meetings = [m for m in source.meetings(session.id) if since <= m.date.date() <= until]
    batch.meetings = len(meetings)

    subjects: dict[int, SubjectInfo] = {}
    debates: dict[int, set[Debate]] = defaultdict(set)
    for meeting in meetings:
        for subject in source.subjects(meeting.id):
            info = SubjectInfo.from_rows(subject, meeting)
            subjects[info.subject_id] = info
            for business in info.businesses:
                debates[business.business_id].add(Debate(info.date, info.council))
    batch.subjects = len(subjects)

    for day in sorted({m.date.date() for m in meetings}):
        for transcript in source.transcripts(session.id, day):
            batch.transcripts += 1
            subject_info = subjects.get(transcript.subject_id)
            if subject_info is None:
                logger.warning("Votum %s ohne bekanntes Traktandum übersprungen", transcript.id)
                batch.skipped_transcripts += 1
                continue
            document = map_transcript(transcript, subject_info)
            if document is None or document.language not in languages:
                batch.skipped_transcripts += 1
                continue
            batch.documents.append(document)

    business_ids = sorted(debates)
    batch.businesses = len(business_ids)
    for language in sorted(languages):
        for ids in batched(business_ids, BUSINESS_BATCH_SIZE):
            for row in source.businesses(list(ids), ODATA_LANGUAGE[language]):
                document = map_business(row, debates.get(row.id, ()))
                if document is not None:
                    batch.documents.append(document)
    return batch


def iter_session_batches(
    source: Source, since: dt.date, until: dt.date, languages: frozenset[Language]
) -> Iterator[SessionBatch]:
    for session in source.sessions(since, until):
        logger.info("Session %s (%s)", session.name, session.id)
        yield collect_session(source, session, since, until, languages)


def run_ingest(
    source: Source,
    session_factory: Callable[[], Session],
    since: dt.date,
    until: dt.date,
    languages: frozenset[Language],
) -> IngestStats:
    """Lädt, bildet ab und speichert; ein Commit pro Session."""
    stats = IngestStats()
    for batch in iter_session_batches(source, since, until, languages):
        with session_factory() as db, db.begin():
            stored = upsert_documents(db, batch.documents)
        stats.add(batch, stored)
        logger.info(
            "Session %s: %d Dokumente (neu %d, geändert %d, unverändert %d)",
            batch.session.name,
            len(batch.documents),
            stored.inserted,
            stored.updated,
            stored.unchanged,
        )
    return stats
