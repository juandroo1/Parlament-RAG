"""Idempotentes Schreiben in `documents` (Entscheidungsprotokoll, Task 1.3).

- Neu: einfügen.
- Gleicher `raw_hash`: nichts tun.
- Anderer `raw_hash`: aktualisieren und die Chunks des Dokuments löschen, damit der
  Index-Befehl es neu indexiert.
- Geschäfte: `debate_dates` und `debate_councils` werden mit dem Bestand vereinigt,
  damit Läufe über verschiedene Zeiträume frühere Debatten nicht überschreiben.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from sqlalchemy import delete, select, tuple_
from sqlalchemy.orm import Session

from parlrag.db.models import Chunk, Document
from parlrag.ingest.mapping import DocumentData

Key = tuple[str, str, str]
_LOOKUP_BATCH = 500


@dataclass
class UpsertResult:
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0

    def __iadd__(self, other: "UpsertResult") -> "UpsertResult":
        self.inserted += other.inserted
        self.updated += other.updated
        self.unchanged += other.unchanged
        return self


def _key(document: DocumentData) -> Key:
    return (document.source_type, document.source_id, document.language)


def _existing(session: Session, keys: Sequence[Key]) -> dict[Key, Document]:
    found: dict[Key, Document] = {}
    for start in range(0, len(keys), _LOOKUP_BATCH):
        batch = keys[start : start + _LOOKUP_BATCH]
        statement = select(Document).where(
            tuple_(Document.source_type, Document.source_id, Document.language).in_(batch)
        )
        for row in session.scalars(statement):
            found[(row.source_type, row.source_id, row.language)] = row
    return found


def _merge_debates(document: DocumentData, existing: Document) -> DocumentData:
    if document.source_type != "business":
        return document
    dates = tuple(sorted(set(existing.debate_dates) | set(document.debate_dates)))
    councils = tuple(sorted(set(existing.debate_councils) | set(document.debate_councils)))
    return document.model_copy(update={"debate_dates": dates, "debate_councils": councils})


def upsert_documents(session: Session, documents: Iterable[DocumentData]) -> UpsertResult:
    """Schreibt die Dokumente; committet nicht (das macht der Aufrufer pro Session)."""
    by_key: dict[Key, DocumentData] = {}
    for document in documents:
        by_key[_key(document)] = document  # bei Doppelten gewinnt das letzte
    existing = _existing(session, list(by_key))

    result = UpsertResult()
    for key, document in by_key.items():
        current = existing.get(key)
        if current is None:
            session.add(Document(**document.to_row()))
            result.inserted += 1
            continue
        merged = _merge_debates(document, current)
        if merged.raw_hash == current.raw_hash:
            result.unchanged += 1
            continue
        for column, value in merged.to_row().items():
            setattr(current, column, value)
        session.execute(delete(Chunk).where(Chunk.document_id == current.id))
        result.updated += 1
    session.flush()
    return result
