"""Ein- und Ausgabe von `POST /ask` (plan.md, Abschnitt 8)."""

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from parlrag.generation.pipeline import AskResult
from parlrag.query.speakers import Speaker
from parlrag.retrieval import SearchFilters


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(
        min_length=3, max_length=500, description="Frage auf Deutsch oder Französisch."
    )
    filters: SearchFilters | None = Field(
        default=None, description="Rat, Zeitraum, Fraktion, Person; wie bei `parlrag search`."
    )
    detect: bool = Field(
        default=True,
        description="Person und Zeitraum aus der Frage erkennen und als Filter anwenden "
        "(gesetzte Filter haben Vorrang).",
    )


class Source(BaseModel):
    """Eine zitierte Quelle mit allem für die Quellenangabe (AK-2.1, AK-2.2)."""

    number: int = Field(description="Nummer [n] im Antworttext.")
    source_key: str = Field(description="Dokument-ID `<source_type>:<source_id>`.")
    source_type: str
    language: str
    title: str
    speaker_name: str | None
    speaker_function: str | None
    parl_group: str | None
    canton: str | None
    council: str | None
    date: dt.date
    business_numbers: list[str]
    section: str | None
    text: str = Field(description="Ausschnitt: der übergebene Abschnitt im Wortlaut.")
    url: str = Field(description="Originalstelle auf parlament.ch.")


class Usage(BaseModel):
    model: str | None = Field(description="Modell, das geantwortet hat; null ohne LLM-Aufruf.")
    backend: str | None
    input_tokens: int = Field(description="Input-Tokens inklusive Cache.")
    output_tokens: int
    cost_usd: float | None = Field(description="Geschätzte Kosten; null bei unbekanntem Preis.")
    cost_estimated: bool = Field(description="true beim Claude-Abo: Schätzung, nicht verrechnet.")
    latency_ms: float = Field(description="Dauer der ganzen Anfrage.")


class AppliedFilters(BaseModel):
    applied: SearchFilters = Field(description="Filter der Suche: gesetzt plus erkannt.")
    detected: list[str] = Field(
        description="Aus der Frage erkannte Filter: speaker, date_from, date_to."
    )


class Coverage(BaseModel):
    first: dt.date = Field(description="Erstes Datum der Voten im Korpus.")
    last: dt.date = Field(description="Letztes Datum der Voten im Korpus.")
    partial: bool = Field(description="Der gefragte Zeitraum geht über die Daten hinaus.")


class AskResponse(BaseModel):
    answer: str
    insufficient_context: bool
    insufficient_reason: str | None = Field(
        description="no_hits, low_similarity, model oder out_of_range; null bei einer Antwort."
    )
    sources: list[Source]
    usage: Usage
    filters: AppliedFilters
    coverage: Coverage | None = Field(description="Abgedeckter Zeitraum; null ohne Voten.")
    speaker_candidates: list[Speaker] = Field(
        description="Bei einem mehrdeutigen Namen die möglichen Personen, sonst leer."
    )
    retried_without: list[str] = Field(
        description="Ohne diese erkannten Filter neu gesucht (z. B. speaker), sonst leer."
    )


def to_response(result: AskResult, latency_ms: float) -> AskResponse:
    answer = result.answer
    usage = answer.usage
    return AskResponse(
        answer=answer.answer,
        insufficient_context=answer.insufficient_context,
        insufficient_reason=answer.insufficient_reason,
        sources=[
            Source(
                number=source.number,
                source_key=source.hit.source_key,
                source_type=source.hit.source_type,
                language=source.hit.language,
                title=source.hit.title,
                speaker_name=source.hit.speaker_name,
                speaker_function=source.hit.speaker_function,
                parl_group=source.hit.parl_group,
                canton=source.hit.canton,
                council=source.hit.council,
                date=source.hit.date,
                business_numbers=list(source.hit.business_numbers),
                section=source.hit.section,
                text=source.hit.text,
                url=source.hit.url,
            )
            for source in answer.sources
        ],
        usage=Usage(
            model=usage.model if usage else None,
            backend=usage.backend if usage else None,
            input_tokens=(
                usage.input_tokens
                + usage.cache_creation_input_tokens
                + usage.cache_read_input_tokens
                if usage
                else 0
            ),
            output_tokens=usage.output_tokens if usage else 0,
            cost_usd=(usage.cost_usd if usage else 0.0),
            cost_estimated=bool(usage and usage.backend == "claude-code"),
            latency_ms=round(latency_ms, 1),
        ),
        filters=AppliedFilters(applied=result.filters, detected=list(result.detected)),
        coverage=(
            Coverage(
                first=result.coverage.first,
                last=result.coverage.last,
                partial=result.coverage.partial,
            )
            if result.coverage
            else None
        ),
        speaker_candidates=list(result.speaker_candidates),
        retried_without=list(result.retried_without),
    )
