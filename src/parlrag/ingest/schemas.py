"""Pydantic-Modelle für OData-Zeilen (Systemgrenze, CLAUDE.md).

Nur die Felder, die das Mapping braucht; alles andere wird ignoriert. Besonderheiten
des Dienstes (plan.md, Abschnitt 3):
- Datumswerte kommen als `/Date(<ms>)/` und sind Schweizer Ortszeit, als UTC kodiert.
- Int64-Werte (z. B. `Transcript.ID`) kommen als String und werden zu `int`.
- `Transcript.MeetingDate` ist Text im Format `YYYYMMDD`.
"""

import datetime as dt
import re
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator

_ODATA_DATE = re.compile(r"/Date\((-?\d+)(?:[+-]\d{4})?\)/")
_EPOCH = dt.datetime(1970, 1, 1)


def parse_odata_datetime(value: Any) -> Any:
    """`/Date(ms)/` → naive datetime; die UTC-Komponenten sind die lokale Schweizer Zeit."""
    if isinstance(value, str):
        match = _ODATA_DATE.fullmatch(value)
        if match:
            return _EPOCH + dt.timedelta(milliseconds=int(match.group(1)))
    return value


def parse_compact_date(value: Any) -> Any:
    if isinstance(value, str) and re.fullmatch(r"\d{8}", value):
        return dt.date(int(value[:4]), int(value[4:6]), int(value[6:]))
    return value


ODataDateTime = Annotated[dt.datetime, BeforeValidator(parse_odata_datetime)]
CompactDate = Annotated[dt.date, BeforeValidator(parse_compact_date)]


def _unwrap_collection(value: Any) -> Any:
    """Expandierte Navigationsfelder: Liste, `{"results": [...]}` oder unexpandiert."""
    if isinstance(value, dict):
        if "results" in value:
            return value["results"]
        if "__deferred" in value:
            return []
    return value


class ODataRow(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True, frozen=True)


class SessionRow(ODataRow):
    id: int = Field(alias="ID")
    name: str = Field(alias="SessionName")
    start_date: ODataDateTime = Field(alias="StartDate")
    end_date: ODataDateTime = Field(alias="EndDate")


class MeetingRow(ODataRow):
    id: int = Field(alias="ID")
    session_id: int = Field(alias="IdSession")
    council: int = Field(alias="Council")
    date: ODataDateTime = Field(alias="Date")


class SubjectBusinessRow(ODataRow):
    business_number: int = Field(alias="BusinessNumber")
    short_number: str = Field(alias="BusinessShortNumber")
    title_de: str | None = Field(default=None, alias="TitleDE")
    title_fr: str | None = Field(default=None, alias="TitleFR")
    sort_order: int | None = Field(default=None, alias="SortOrder")


class SubjectRow(ODataRow):
    id: int = Field(alias="ID")
    meeting_id: int = Field(alias="IdMeeting")
    sort_order: int | None = Field(default=None, alias="SortOrder")
    businesses: list[SubjectBusinessRow] = Field(default_factory=list, alias="SubjectsBusiness")

    @field_validator("businesses", mode="before")
    @classmethod
    def _unwrap(cls, value: Any) -> Any:
        return _unwrap_collection(value)


class TranscriptRow(ODataRow):
    id: int = Field(alias="ID")
    language: str = Field(alias="Language")
    subject_id: int = Field(alias="IdSubject")
    type: int = Field(alias="Type")
    text: str | None = Field(default=None, alias="Text")
    language_of_text: str | None = Field(default=None, alias="LanguageOfText")
    speaker_full_name: str | None = Field(default=None, alias="SpeakerFullName")
    speaker_function: str | None = Field(default=None, alias="SpeakerFunction")
    parl_group: str | None = Field(default=None, alias="ParlGroupAbbreviation")
    canton: str | None = Field(default=None, alias="CantonAbbreviation")
    meeting_date: CompactDate = Field(alias="MeetingDate")
    session_id: int | None = Field(default=None, alias="IdSession")
    sort_order: int = Field(alias="SortOrder")


class BusinessRow(ODataRow):
    id: int = Field(alias="ID")
    language: str = Field(alias="Language")
    short_number: str = Field(alias="BusinessShortNumber")
    title: str = Field(alias="Title")
    description: str | None = Field(default=None, alias="Description")
    initial_situation: str | None = Field(default=None, alias="InitialSituation")
    submitted_text: str | None = Field(default=None, alias="SubmittedText")
    reason_text: str | None = Field(default=None, alias="ReasonText")
    federal_council_response_text: str | None = Field(
        default=None, alias="FederalCouncilResponseText"
    )
    submission_date: ODataDateTime | None = Field(default=None, alias="SubmissionDate")
