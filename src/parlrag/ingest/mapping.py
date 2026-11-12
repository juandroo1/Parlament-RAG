"""Abbildung der OData-Zeilen auf Datensätze der Tabelle `documents` (plan.md, Abschnitte 3 und 4).

Regeln aus dem Entscheidungsprotokoll:
- Voten: nur `Type = 1` mit `LanguageOfText` DE oder FR; die Sprache des Dokuments ist
  `LanguageOfText`. Der Rat kommt aus der Sitzung (`Meeting.Council`), nicht aus
  `Transcript.CouncilId` (Rat des Redners).
- Geschäfte: ein Dokument pro Sprachzeile, Text aus Abschnitten mit Überschriften,
  `date` = Einreichungsdatum, Filter über `debate_dates` und `debate_councils` (AK-4.3).
- `raw_hash` ist ein Hash über den abgebildeten Inhalt.
"""

import datetime as dt
import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from parlrag.ingest.schemas import BusinessRow, MeetingRow, SubjectRow, TranscriptRow
from parlrag.ingest.text import clean_markup

Language = Literal["de", "fr"]
Council = Literal["NR", "SR", "V"]

LANGUAGES: dict[str, Language] = {"DE": "de", "FR": "fr"}
COUNCILS: dict[int, Council] = {1: "NR", 2: "SR", 3: "V"}
VOTUM_TYPE = 1

AB_URL = (
    "https://www.parlament.ch/{lang}/ratsbetrieb/amtliches-bulletin/"
    "amtliches-bulletin-die-verhandlungen?SubjectId={subject_id}#votum{sort_order}"
)
CURIA_URL = "https://www.parlament.ch/{lang}/ratsbetrieb/suche-curia-vista/geschaeft?AffairId={id}"

# Abschnitte eines Geschäftsdokuments, in dieser Reihenfolge (Entscheidungsprotokoll, Task 1.2).
BUSINESS_SECTIONS: tuple[tuple[str, dict[Language, str]], ...] = (
    ("description", {"de": "Beschreibung", "fr": "Description"}),
    ("initial_situation", {"de": "Ausgangslage", "fr": "Situation initiale"}),
    ("submitted_text", {"de": "Eingereichter Text", "fr": "Texte déposé"}),
    ("reason_text", {"de": "Begründung", "fr": "Développement"}),
    (
        "federal_council_response_text",
        {"de": "Stellungnahme des Bundesrates", "fr": "Avis du Conseil fédéral"},
    ),
)
SECTION_PREFIX = "## "
FALLBACK_TITLE: dict[Language, str] = {"de": "Ratsdebatte", "fr": "Débat parlementaire"}


class DocumentData(BaseModel):
    """Ein Datensatz für `documents`, validiert gegen die Constraints der Datenbank."""

    model_config = ConfigDict(frozen=True)

    source_type: Literal["transcript", "business"]
    source_id: str = Field(min_length=1)
    language: Language
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    speaker_name: str | None = None
    speaker_function: str | None = None
    parl_group: str | None = None
    canton: str | None = None
    council: Council | None = None
    date: dt.date
    debate_dates: tuple[dt.date, ...] = ()
    debate_councils: tuple[Council, ...] = ()
    business_numbers: tuple[str, ...] = ()
    session_id: int | None = None
    subject_id: int | None = None
    sort_order: int | None = None
    url: str

    @property
    def raw_hash(self) -> str:
        """SHA-256 über alle Felder; ändert sich nur, wenn sich der Inhalt ändert."""
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @classmethod
    def from_record(cls, record: Any) -> "DocumentData":
        """Aus einer Zeile von `documents` (ORM-Objekt) zurück in ein validiertes Dokument."""
        return cls.model_validate({name: getattr(record, name) for name in cls.model_fields})

    def to_row(self) -> dict[str, Any]:
        """Spaltenwerte für `documents` (ohne `id`)."""
        row = self.model_dump()
        for key in ("debate_dates", "debate_councils", "business_numbers"):
            row[key] = list(row[key])
        row["raw_hash"] = self.raw_hash
        return row


@dataclass(frozen=True)
class BusinessRef:
    business_id: int
    short_number: str
    titles: dict[Language, str | None]


@dataclass(frozen=True)
class SubjectInfo:
    """Kontext eines Traktandums, den alle seine Voten teilen."""

    subject_id: int
    session_id: int
    council: Council
    date: dt.date
    businesses: tuple[BusinessRef, ...]

    @classmethod
    def from_rows(cls, subject: SubjectRow, meeting: MeetingRow) -> "SubjectInfo":
        if subject.meeting_id != meeting.id:
            raise ValueError(f"Traktandum {subject.id} gehört nicht zu Sitzung {meeting.id}")
        if meeting.council not in COUNCILS:
            raise ValueError(f"Unbekannter Rat {meeting.council} in Sitzung {meeting.id}")
        businesses = tuple(
            BusinessRef(
                business_id=item.business_number,
                short_number=item.short_number,
                titles={"de": item.title_de, "fr": item.title_fr},
            )
            for item in sorted(
                subject.businesses, key=lambda b: (b.sort_order or 0, b.short_number)
            )
        )
        return cls(
            subject_id=subject.id,
            session_id=meeting.session_id,
            council=COUNCILS[meeting.council],
            date=meeting.date.date(),
            businesses=businesses,
        )

    def title(self, language: Language) -> str:
        parts = []
        for business in self.businesses:
            title = business.titles.get(language) or business.titles.get("de")
            parts.append(f"{business.short_number} {title}" if title else business.short_number)
        return "; ".join(parts) or FALLBACK_TITLE[language]


@dataclass(frozen=True)
class Debate:
    """Eine Behandlung eines Geschäfts im Rat (für `debate_dates` und `debate_councils`)."""

    date: dt.date
    council: Council


def has_content(text: str) -> bool:
    """Mindestens ein Buchstabe oder eine Ziffer; Platzhalter wie «-» zählen nicht als Text."""
    return any(character.isalnum() for character in text)


def map_transcript(row: TranscriptRow, subject: SubjectInfo) -> DocumentData | None:
    """Votum → Dokument; `None` für Verfahrenstexte, andere Sprachen und leere Texte."""
    if row.subject_id != subject.subject_id:
        raise ValueError(f"Votum {row.id} gehört nicht zu Traktandum {subject.subject_id}")
    language = LANGUAGES.get(row.language_of_text or "")
    if row.type != VOTUM_TYPE or language is None:
        return None
    text = clean_markup(row.text)
    if not has_content(text):
        return None
    return DocumentData(
        source_type="transcript",
        source_id=str(row.id),
        language=language,
        title=subject.title(language),
        text=text,
        speaker_name=row.speaker_full_name or None,
        speaker_function=row.speaker_function or None,
        parl_group=row.parl_group or None,
        canton=row.canton or None,
        council=subject.council,
        date=row.meeting_date,
        business_numbers=tuple(b.short_number for b in subject.businesses),
        session_id=subject.session_id,
        subject_id=subject.subject_id,
        sort_order=row.sort_order,
        url=AB_URL.format(lang=language, subject_id=subject.subject_id, sort_order=row.sort_order),
    )


def map_business(row: BusinessRow, debates: Iterable[Debate]) -> DocumentData | None:
    """Geschäft (eine Sprachzeile) → Dokument; `None` ohne Text oder in anderer Sprache."""
    language = LANGUAGES.get(row.language)
    if language is None:
        return None
    sections = []
    for field, headings in BUSINESS_SECTIONS:
        body = clean_markup(getattr(row, field))
        if has_content(body):
            sections.append(f"{SECTION_PREFIX}{headings[language]}\n\n{body}")
    if not sections:
        return None

    debate_list = list(debates)
    debate_dates = tuple(sorted({d.date for d in debate_list}))
    debate_councils = tuple(sorted({d.council for d in debate_list}))
    if row.submission_date is not None:
        date = row.submission_date.date()
    elif debate_dates:
        date = debate_dates[0]
    else:
        return None

    return DocumentData(
        source_type="business",
        source_id=str(row.id),
        language=language,
        title=row.title.strip(),
        text="\n\n".join(sections),
        date=date,
        debate_dates=debate_dates,
        debate_councils=debate_councils,
        business_numbers=(row.short_number,),
        url=CURIA_URL.format(lang=language, id=row.id),
    )
