"""Hält die in Task 0.2 verifizierten Annahmen über den OData-Dienst fest.

Die Tests prüfen nur gespeicherte Fixtures (siehe `tests/fixtures/odata/README.md`).
Ändert sich der Dienst und werden die Fixtures neu abgerufen, zeigen rote Tests,
welche Annahme in `plan.md`, Abschnitt 3, nicht mehr stimmt.
"""

import json
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "odata"
EDM = "{http://schemas.microsoft.com/ado/2009/11/edm}"
DATE_PATTERN = re.compile(r"/Date\((-?\d+)\)/")

Row = dict[str, Any]


def load_rows(name: str) -> list[Row]:
    """Liest eine OData-v3-Antwort; akzeptiert `{"d": [...]}` und `{"d": {"results": [...]}}`."""
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    data = payload["d"]
    if isinstance(data, dict):
        data = data["results"]
    assert isinstance(data, list)
    return data


def parse_date(value: str) -> datetime:
    match = DATE_PATTERN.fullmatch(value)
    assert match, value
    return datetime.fromtimestamp(int(match.group(1)) / 1000, tz=UTC)


def entity_properties(entity: str) -> set[str]:
    root = ET.parse(FIXTURES / "metadata.xml").getroot()
    for node in root.iter(f"{EDM}EntityType"):
        if node.get("Name") == entity:
            return {p.get("Name", "") for p in node.iter(f"{EDM}Property")}
    raise AssertionError(f"EntityType {entity} fehlt")


@pytest.fixture(scope="module")
def transcripts_de() -> dict[int, Row]:
    return {int(r["ID"]): r for r in load_rows("transcript_subject82315_de.json")}


@pytest.fixture(scope="module")
def transcripts_fr() -> dict[int, Row]:
    return {int(r["ID"]): r for r in load_rows("transcript_subject82315_fr.json")}


def test_readme_lists_exactly_the_fixture_files() -> None:
    readme = (FIXTURES / "README.md").read_text(encoding="utf-8")
    listed = set(re.findall(r"^\| `([^`]+)` \|", readme, flags=re.MULTILINE))
    present = {p.name for p in FIXTURES.iterdir() if p.name != "README.md"}
    assert listed == present


@pytest.mark.parametrize(
    ("entity", "fields"),
    [
        ("Session", {"ID", "Language", "SessionName", "StartDate", "LegislativePeriodNumber"}),
        ("Meeting", {"ID", "IdSession", "Council", "Date"}),
        ("Subject", {"ID", "IdMeeting", "SortOrder"}),
        ("SubjectBusiness", {"IdSubject", "BusinessNumber", "BusinessShortNumber", "Title"}),
        (
            "Transcript",
            {
                "ID",
                "Language",
                "IdSubject",
                "Type",
                "Text",
                "LanguageOfText",
                "SpeakerFullName",
                "SpeakerFunction",
                "ParlGroupAbbreviation",
                "CantonAbbreviation",
                "CouncilId",
                "MeetingCouncilAbbreviation",
                "MeetingDate",
                "IdSession",
                "SortOrder",
                "DisplaySpeaker",
            },
        ),
        (
            "Business",
            {
                "ID",
                "Language",
                "BusinessShortNumber",
                "Title",
                "SubmittedText",
                "ReasonText",
                "FederalCouncilResponseText",
                "SubmissionDate",
                "SubmissionCouncil",
            },
        ),
    ],
)
def test_metadata_contains_fields_the_plan_relies_on(entity: str, fields: set[str]) -> None:
    assert fields <= entity_properties(entity)


def test_dates_are_swiss_local_time_encoded_as_utc() -> None:
    sessions = {r["ID"]: r for r in load_rows("session_legislature52_de.json")}
    autumn_2026 = sessions[5215]
    assert autumn_2026["SessionName"] == "Herbstsession 2026"
    # Sessionsbeginn ist Montag, 14.09.2026: Mitternacht in UTC, also eigentlich Ortszeit.
    assert parse_date(autumn_2026["StartDate"]) == datetime(2026, 9, 14, tzinfo=UTC)


def test_int64_values_are_serialized_as_strings(transcripts_de: dict[int, Row]) -> None:
    # Int64-Felder (z. B. Subject.ID, Transcript.ID, Transcript.IdSubject) kommen als String,
    # Int32-Felder (z. B. Session.ID, Business.ID) als Zahl.
    (subject,) = [r for r in load_rows("subject_meeting5262_de.json") if r["ID"] == "82315"]
    assert isinstance(subject["IdMeeting"], str)
    votum = transcripts_de[418982]
    assert isinstance(votum["ID"], str)
    assert isinstance(votum["IdSubject"], str)
    assert isinstance(load_rows("session_legislature52_de.json")[0]["ID"], int)
    assert isinstance(load_rows("business_20253906_de.json")[0]["ID"], int)


def test_subject_can_cover_several_businesses() -> None:
    subjects = {int(r["ID"]): r for r in load_rows("subject_meeting5262_de.json")}
    links = subjects[82315]["SubjectsBusiness"]
    links = links["results"] if isinstance(links, dict) else links
    short_numbers = {b["BusinessShortNumber"] for b in links}
    assert short_numbers == {"25.3866", "25.3902", "25.3906"}
    assert {b["BusinessNumber"] for b in links} >= {20253906}


def test_transcript_text_is_identical_in_all_language_rows(
    transcripts_de: dict[int, Row], transcripts_fr: dict[int, Row]
) -> None:
    assert transcripts_de.keys() == transcripts_fr.keys()
    for transcript_id, de in transcripts_de.items():
        fr = transcripts_fr[transcript_id]
        assert de["Language"] == "DE"
        assert fr["Language"] == "FR"
        assert de["Text"] == fr["Text"]
        assert de["LanguageOfText"] == fr["LanguageOfText"]


def test_language_neutral_fields_do_not_change_between_language_rows(
    transcripts_de: dict[int, Row], transcripts_fr: dict[int, Row]
) -> None:
    neutral = [
        "ParlGroupAbbreviation",
        "CantonAbbreviation",
        "CouncilId",
        "SpeakerFunction",
        "MeetingCouncilAbbreviation",
        "SortOrder",
        "Type",
    ]
    for transcript_id, de in transcripts_de.items():
        for field in neutral:
            assert de[field] == transcripts_fr[transcript_id][field], field
    # Fraktionsnamen sind dagegen übersetzt.
    michel = 418982
    assert transcripts_de[michel]["ParlGroupName"] != transcripts_fr[michel]["ParlGroupName"]


def test_original_language_is_in_language_of_text(transcripts_de: dict[int, Row]) -> None:
    languages = {r["LanguageOfText"] for r in transcripts_de.values()}
    assert languages <= {"DE", "FR", "IT", None}
    assert transcripts_de[418885]["LanguageOfText"] == "FR"  # Crevoisier Crelier, auf Französisch
    assert transcripts_de[418982]["LanguageOfText"] == "DE"  # Michel, auf Deutsch


def test_entry_types_and_procedural_entries(transcripts_de: dict[int, Row]) -> None:
    procedural = transcripts_de[418822]
    assert procedural["Type"] == 2
    assert not procedural["SpeakerFullName"]
    assert "Abstimmung" in procedural["Text"]

    president = transcripts_de[418871]
    assert president["Type"] == 1
    assert president["LanguageOfText"] is None
    assert president["DisplaySpeaker"] is False

    indexable = [
        r for r in transcripts_de.values() if r["Type"] == 1 and r["LanguageOfText"] in {"DE", "FR"}
    ]
    assert len(indexable) == 6
    assert all(r["SpeakerFullName"] for r in indexable)


def test_federal_council_member_has_no_parl_group(transcripts_de: dict[int, Row]) -> None:
    baume_schneider = transcripts_de[418840]
    assert baume_schneider["CouncilId"] == 99
    assert baume_schneider["SpeakerFunction"] == "BR-F"
    assert baume_schneider["ParlGroupAbbreviation"] is None


def test_transcript_markup_and_placeholders(transcripts_de: dict[int, Row]) -> None:
    texts = [r["Text"] for r in transcripts_de.values()]
    assert all(t.startswith("<pd_text>") and t.rstrip().endswith("</pd_text>") for t in texts)
    joined = "".join(texts)
    for placeholder in ["[GZ]", "[VS]", "[NB]"]:
        assert placeholder in joined
    assert re.search(r"\[PAGE \d+\]", joined)


def test_sort_order_is_unique_within_a_subject(transcripts_de: dict[int, Row]) -> None:
    sort_orders = [r["SortOrder"] for r in transcripts_de.values()]
    assert len(sort_orders) == len(set(sort_orders))


def test_business_texts_are_real_translations() -> None:
    (de,) = load_rows("business_20253906_de.json")
    (fr,) = load_rows("business_20253906_fr.json")
    assert de["ID"] == fr["ID"] == 20253906
    assert de["BusinessShortNumber"] == fr["BusinessShortNumber"] == "25.3906"
    for field in ["Title", "SubmittedText", "ReasonText", "FederalCouncilResponseText"]:
        assert de[field] and fr[field]
        assert de[field] != fr[field], field
    assert "<p>" in de["SubmittedText"]
    # Abkürzungen sind übersetzt, die numerische ID nicht.
    assert de["SubmissionCouncilAbbreviation"] == "NR"
    assert fr["SubmissionCouncilAbbreviation"] == "CN"
    assert de["SubmissionCouncil"] == fr["SubmissionCouncil"]
