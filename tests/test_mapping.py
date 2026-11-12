"""Mapping der echten Fixtures auf `documents` (Task 1.2)."""

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import inspect as sa_inspect

from parlrag.db.models import Document
from parlrag.ingest.mapping import (
    Debate,
    DocumentData,
    SubjectInfo,
    map_business,
    map_transcript,
)
from parlrag.ingest.schemas import BusinessRow, MeetingRow, SubjectRow, TranscriptRow

FIXTURES = Path(__file__).parent / "fixtures" / "odata"


def rows(name: str) -> list[dict[str, Any]]:
    data = json.loads((FIXTURES / name).read_text(encoding="utf-8"))["d"]
    result = data["results"] if isinstance(data, dict) else data
    assert isinstance(result, list)
    return result


@pytest.fixture(scope="module")
def pfas_subject() -> SubjectInfo:
    subject = next(
        SubjectRow.model_validate(r)
        for r in rows("subject_meeting5262_de.json")
        if r["ID"] == "82315"
    )
    meeting = next(
        MeetingRow.model_validate(r)
        for r in rows("meeting_session5215_de.json")
        if r["ID"] == "5262"
    )
    return SubjectInfo.from_rows(subject, meeting)


@pytest.fixture(scope="module")
def pfas_documents(pfas_subject: SubjectInfo) -> dict[str, DocumentData]:
    transcripts = [TranscriptRow.model_validate(r) for r in rows("transcript_subject82315_de.json")]
    documents = [map_transcript(t, pfas_subject) for t in transcripts]
    return {d.source_id: d for d in documents if d is not None}


# --- Schemas -------------------------------------------------------------------------


def test_odata_dates_are_swiss_local_time() -> None:
    meeting = MeetingRow.model_validate(rows("meeting_session5215_de.json")[0])
    assert meeting.date == dt.datetime(2026, 9, 14)  # Sessionsbeginn, Mitternacht Ortszeit


def test_int64_strings_and_compact_dates_are_converted() -> None:
    transcript = TranscriptRow.model_validate(rows("transcript_subject82315_de.json")[0])
    assert transcript.id == 418868
    assert transcript.subject_id == 82315
    assert transcript.session_id == 5215
    assert transcript.meeting_date == dt.date(2026, 9, 15)


def test_meeting_councils_cover_nr_sr_and_united_assembly() -> None:
    councils = {MeetingRow.model_validate(r).council for r in rows("meeting_session5215_de.json")}
    assert councils == {1, 2, 3}


# --- Voten ---------------------------------------------------------------------------


def test_subject_info_comes_from_meeting(pfas_subject: SubjectInfo) -> None:
    assert pfas_subject.council == "SR"
    assert pfas_subject.date == dt.date(2026, 9, 15)
    assert pfas_subject.session_id == 5215
    assert [b.short_number for b in pfas_subject.businesses] == ["25.3866", "25.3902", "25.3906"]


def test_only_real_speeches_in_german_or_french_are_mapped(
    pfas_documents: dict[str, DocumentData],
) -> None:
    # 11 Einträge: 4 präsidiale Verfahrensvoten ohne Sprache und 1 Verfahrenstext fallen weg.
    assert set(pfas_documents) == {"418941", "418885", "418982", "418936", "418938", "418840"}
    languages = {source_id: d.language for source_id, d in pfas_documents.items()}
    assert languages["418885"] == "fr"  # Crevoisier Crelier
    assert languages["418840"] == "fr"  # Baume-Schneider
    assert [lang for lang in languages.values()].count("de") == 4


def test_transcript_metadata_for_citations(pfas_documents: dict[str, DocumentData]) -> None:
    michel = pfas_documents["418982"]
    assert michel.source_type == "transcript"
    assert michel.speaker_name == "Michel Matthias"
    assert michel.parl_group == "RL"
    assert michel.canton == "ZG"
    assert michel.council == "SR"
    assert michel.date == dt.date(2026, 9, 15)
    assert michel.business_numbers == ("25.3866", "25.3902", "25.3906")
    assert michel.subject_id == 82315
    assert michel.sort_order == 6
    assert michel.url == (
        "https://www.parlament.ch/de/ratsbetrieb/amtliches-bulletin/"
        "amtliches-bulletin-die-verhandlungen?SubjectId=82315#votum6"
    )
    assert michel.title.startswith("25.3866 ")
    assert "; 25.3902 " in michel.title


def test_federal_council_member_has_no_parl_group(pfas_documents: dict[str, DocumentData]) -> None:
    baume_schneider = pfas_documents["418840"]
    assert baume_schneider.speaker_function == "BR-F"
    assert baume_schneider.parl_group is None
    assert baume_schneider.url.startswith("https://www.parlament.ch/fr/")


def test_french_speech_gets_french_title(pfas_documents: dict[str, DocumentData]) -> None:
    german, french = pfas_documents["418982"].title, pfas_documents["418885"].title
    assert german != french
    assert "PFAS" in french


def test_mapped_texts_contain_no_markup(pfas_documents: dict[str, DocumentData]) -> None:
    for document in pfas_documents.values():
        assert not re.search(r"<[a-z/]|\[(?:GZ|VS|NB|NAM|PAGE)", document.text)
    assert pfas_documents["418982"].text.startswith("Die Problematik und das bisher unterschätzte")


def test_german_and_french_language_rows_give_identical_documents(
    pfas_subject: SubjectInfo, pfas_documents: dict[str, DocumentData]
) -> None:
    for raw in rows("transcript_subject82315_fr.json"):
        document = map_transcript(TranscriptRow.model_validate(raw), pfas_subject)
        if document is not None:
            assert document == pfas_documents[document.source_id]


def test_transcript_from_other_subject_is_rejected(pfas_subject: SubjectInfo) -> None:
    raw = dict(rows("transcript_subject82315_de.json")[1], IdSubject="1")
    with pytest.raises(ValueError, match="Traktandum"):
        map_transcript(TranscriptRow.model_validate(raw), pfas_subject)


# --- Geschäfte -----------------------------------------------------------------------


DEBATES = [
    Debate(dt.date(2026, 9, 15), "SR"),
    Debate(dt.date(2026, 3, 10), "NR"),
    Debate(dt.date(2026, 9, 15), "SR"),
]


@pytest.mark.parametrize(
    ("fixture", "language", "headings"),
    [
        (
            "business_20253906_de.json",
            "de",
            ["## Eingereichter Text", "## Begründung", "## Stellungnahme des Bundesrates"],
        ),
        (
            "business_20253906_fr.json",
            "fr",
            ["## Texte déposé", "## Développement", "## Avis du Conseil fédéral"],
        ),
    ],
)
def test_motion_is_mapped_per_language_with_sections(
    fixture: str, language: str, headings: list[str]
) -> None:
    (raw,) = rows(fixture)
    document = map_business(BusinessRow.model_validate(raw), DEBATES)

    assert document is not None
    assert document.source_type == "business"
    assert document.source_id == "20253906"
    assert document.language == language
    assert document.business_numbers == ("25.3906",)
    assert document.date == dt.date(2025, 6, 20)  # Einreichungsdatum
    assert document.debate_dates == (dt.date(2026, 3, 10), dt.date(2026, 9, 15))
    assert document.debate_councils == ("NR", "SR")
    assert document.council is None
    assert document.parl_group is None
    assert document.url == (
        f"https://www.parlament.ch/{language}/ratsbetrieb/suche-curia-vista/geschaeft"
        "?AffairId=20253906"
    )
    positions = [document.text.index(heading + "\n") for heading in headings]
    assert positions == sorted(positions)
    assert document.text.startswith(headings[0])
    assert "<" not in document.text


def test_federal_council_business_uses_description_and_initial_situation() -> None:
    (raw,) = rows("business_20240089_de.json")
    document = map_business(BusinessRow.model_validate(raw), [])

    assert document is not None
    assert document.text.startswith("## Beschreibung\n\nBotschaft vom 20. November 2024")
    assert "\n\n## Ausgangslage\n\nMedienmitteilung des Bundesrates" in document.text
    assert "SDA" not in document.text  # Proceedings (SDA-Meldungen) wird nicht übernommen
    assert document.date == dt.date(2024, 11, 14)
    assert document.debate_dates == ()


def test_business_without_text_or_in_other_language_is_skipped() -> None:
    (raw,) = rows("business_20253906_de.json")
    empty = {**raw, "SubmittedText": None, "ReasonText": "", "FederalCouncilResponseText": None}
    assert map_business(BusinessRow.model_validate(empty), DEBATES) is None
    assert map_business(BusinessRow.model_validate({**raw, "Language": "IT"}), DEBATES) is None


def test_placeholder_sections_without_content_are_dropped() -> None:
    # Gefunden in Task 2.3: Geschäft 23.304 (FR) hat als «Situation initiale» nur «-».
    (raw,) = rows("business_20253906_fr.json")
    document = map_business(
        BusinessRow.model_validate({**raw, "InitialSituation": "<p>-</p>"}), DEBATES
    )
    assert document is not None
    assert "Situation initiale" not in document.text
    assert document.text.startswith("## Texte déposé")


def test_speech_without_letters_or_digits_is_skipped(pfas_subject: SubjectInfo) -> None:
    placeholder = "<pd_text><p>\N{EN DASH} \N{HORIZONTAL ELLIPSIS}</p></pd_text>"
    raw = dict(rows("transcript_subject82315_de.json")[1], Text=placeholder)
    assert map_transcript(TranscriptRow.model_validate(raw), pfas_subject) is None


# --- DocumentData ----------------------------------------------------------------------


def test_raw_hash_is_stable_and_changes_with_content(
    pfas_documents: dict[str, DocumentData],
) -> None:
    document = pfas_documents["418982"]
    assert document.raw_hash == document.model_copy().raw_hash
    assert re.fullmatch(r"[0-9a-f]{64}", document.raw_hash)
    assert document.model_copy(update={"text": document.text + " Nachtrag."}).raw_hash != (
        document.raw_hash
    )


def test_to_row_matches_document_table_columns(pfas_documents: dict[str, DocumentData]) -> None:
    row = pfas_documents["418982"].to_row()
    columns = {column.key for column in sa_inspect(Document).columns} - {"id"}
    assert set(row) == columns
    assert isinstance(row["business_numbers"], list)
