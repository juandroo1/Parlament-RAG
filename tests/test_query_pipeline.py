"""Erkennung in Suche und Pipeline (Task 8.4; Spec 003, AK-16.1 bis AK-16.3, AK-17.2, AK-17.4,
AK-17.5, AK-19.3). Ohne Datenbank, Modell und LLM."""

import dataclasses
import datetime as dt
from typing import Any

import pytest
from sqlalchemy.exc import OperationalError

from parlrag.generation import AnswerGenerator
from parlrag.generation.formatting import answer_payload, format_answer
from parlrag.generation.pipeline import AskPipeline
from parlrag.query import Catalog, Speaker
from parlrag.query.catalog import build_sessions
from parlrag.query.resolve import EMPTY_CATALOG, CatalogCache, Coverage, resolve
from parlrag.query.search import DetectingRetriever
from parlrag.retrieval import SearchFilters, SearchHit
from test_ask import HITS, SPEECH, VALID, FakeLLM, FakeRetriever

D = dt.date
TODAY = D(2026, 11, 24)
FIRST, LAST = D(2023, 12, 4), D(2026, 10, 2)


def _speaker(name: str, *, federal: bool = False, group: str | None = None) -> Speaker:
    return Speaker(
        name=name,
        parl_group=None if federal else group,
        canton="BE",
        council="NR",
        federal_council=federal,
        votes=10,
    )


CATALOG = Catalog(
    first=FIRST,
    last=LAST,
    sessions=build_sessions(
        [(5210, D(2025, 9, 8), D(2025, 9, 26)), (5215, D(2026, 9, 14), D(2026, 10, 2))]
    ),
    speakers=(
        _speaker("Rösti Albert", federal=True),
        _speaker("Funiciello Tamara", group="S"),
        _speaker("Müller Damian", group="RL"),
        _speaker("Müller Leo", group="M-E"),
    ),
)


def year_2025(**changes: Any) -> SearchFilters:
    return SearchFilters(date_from=D(2025, 1, 1), date_to=D(2025, 12, 31), **changes)


# --- Filter auflösen ----------------------------------------------------------------------------


def test_detected_filters_are_applied_and_reported() -> None:
    resolution = resolve("Was sagte Bundesrat Rösti 2025 zum Wolf?", None, CATALOG, TODAY)
    assert resolution.filters == year_2025(speaker="Rösti Albert")
    assert resolution.detected == ("speaker", "date_from", "date_to")
    assert resolution.coverage == Coverage(FIRST, LAST, partial=False)
    assert not resolution.out_of_range


def test_explicit_filters_take_precedence() -> None:
    """AK-17.2: Ein gesetzter Zeitraum ersetzt den erkannten ganz, eine gesetzte Person die
    erkannte; andere gesetzte Filter bleiben."""
    explicit = SearchFilters(council="SR", date_from=D(2024, 1, 1), speaker="Müller Damian")
    resolution = resolve("Was sagte Bundesrat Rösti 2025?", explicit, CATALOG, TODAY)
    assert resolution.filters == explicit
    assert resolution.detected == ()


def test_detection_can_be_switched_off() -> None:
    resolution = resolve("Was sagte Rösti 2025?", None, CATALOG, TODAY, detection=False)
    assert resolution.filters == SearchFilters()
    assert resolution.detected == ()


def test_open_range_keeps_only_the_detected_bound() -> None:
    resolution = resolve("Was sagte Funiciello seit 2025?", None, CATALOG, TODAY)
    assert resolution.filters.date_from == D(2025, 1, 1) and resolution.filters.date_to is None
    assert resolution.detected == ("speaker", "date_from")


@pytest.mark.parametrize(
    "question",
    [
        "Was sagte Tamara Funiciello 2022?",  # vor den Daten
        "Was sagte Rösti in der Frühjahrssession 2027?",  # nach den Daten
        "Was geschah in der Herbstsession 2022?",
    ],
)
def test_period_outside_the_corpus(question: str) -> None:
    resolution = resolve(question, None, CATALOG, TODAY)
    assert resolution.out_of_range
    assert resolution.coverage == Coverage(FIRST, LAST, partial=False)


def test_explicit_period_outside_the_corpus_counts_too() -> None:
    """AK-16.1 gilt auch für gesetzte Filter, auch ohne Erkennung."""
    filters = SearchFilters(date_from=D(2020, 1, 1), date_to=D(2020, 12, 31))
    assert resolve("Wolf", filters, CATALOG, TODAY, detection=False).out_of_range


@pytest.mark.parametrize(
    ("question", "partial"),
    [
        ("Was sagte Funiciello seit 2022?", True),  # beginnt vor den Daten
        ("Was wurde zwischen 2023 und 2024 gesagt?", True),
        ("Was wurde 2026 gesagt?", True),  # endet nach dem 2.10.2026
        ("Was wurde 2025 gesagt?", False),
        ("Was wurde zum Wolf gesagt?", False),
    ],
)
def test_partial_coverage(question: str, partial: bool) -> None:
    resolution = resolve(question, None, CATALOG, TODAY)
    assert not resolution.out_of_range
    assert resolution.coverage is not None and resolution.coverage.partial is partial


def test_without_voten_there_is_no_coverage() -> None:
    resolution = resolve("Was sagte Funiciello 2022?", None, EMPTY_CATALOG, TODAY)
    assert resolution.coverage is None and not resolution.out_of_range


def test_ambiguous_name_gives_candidates_unless_a_speaker_is_set() -> None:
    resolution = resolve("Was sagte Müller zur Stopfleber?", None, CATALOG, TODAY)
    assert [s.name for s in resolution.speaker_candidates] == ["Müller Damian", "Müller Leo"]
    assert resolution.filters.speaker is None
    explicit = SearchFilters(speaker="Müller Leo")
    assert resolve("Was sagte Müller?", explicit, CATALOG, TODAY).speaker_candidates == ()


def _weak(hit: SearchHit) -> SearchHit:
    return dataclasses.replace(hit, vector_similarity=0.40)


def _detecting(retriever: Any, **options: Any) -> DetectingRetriever:
    return DetectingRetriever(
        retriever, lambda: CATALOG, min_similarity=0.55, today=lambda: TODAY, **options
    )


def test_out_of_range_skips_the_search() -> None:
    retriever = FakeRetriever([SPEECH])
    outcome = _detecting(retriever).run("Was sagte Funiciello 2022?", mode="vector")
    assert outcome.hits == [] and outcome.resolution.out_of_range
    assert retriever.calls == []


def test_search_uses_the_applied_filters() -> None:
    retriever = FakeRetriever([SPEECH])
    hits = _detecting(retriever).search("Was sagte Rösti 2025?", mode="vector", top_n=5)
    assert hits == [SPEECH]
    (call,) = retriever.calls
    assert call["filters"] == year_2025(speaker="Rösti Albert")
    assert call["top_n"] == 5


def test_weak_hits_with_detected_speaker_retry_without_it() -> None:
    """AK-17.4: keine passenden Voten der erkannten Person → ohne Personenfilter neu."""
    retriever = FakeRetriever([_weak(SPEECH)])
    outcome = _detecting(retriever).run("Was sagte Funiciello 2025 zum Wolf?", mode="vector")
    assert [call["filters"] for call in retriever.calls] == [
        year_2025(speaker="Funiciello Tamara"),
        year_2025(),  # der Zeitraum bleibt
    ]
    assert outcome.retried_without == ("speaker",)
    assert outcome.resolution.detected == ("date_from", "date_to")


def test_no_retry_with_good_hits_or_a_set_speaker() -> None:
    retriever = FakeRetriever([SPEECH])
    assert _detecting(retriever).run("Was sagte Funiciello?").retried_without == ()
    weak = FakeRetriever([_weak(SPEECH)])
    outcome = _detecting(weak).run("Wolf", SearchFilters(speaker="Funiciello Tamara"))
    assert outcome.retried_without == () and len(weak.calls) == 1


def test_disabled_detection_passes_filters_through() -> None:
    retriever = FakeRetriever([SPEECH])
    _detecting(retriever, enabled=False).search("Was sagte Rösti 2025?")
    assert retriever.calls[0]["filters"] == SearchFilters()


def test_wrapper_exposes_the_retriever_attributes() -> None:
    retriever = FakeRetriever([SPEECH])
    assert _detecting(retriever).embedder is retriever.embedder


# --- Pipeline -------------------------------------------------------------------------------


def _pipeline(hits: list[SearchHit]) -> tuple[AskPipeline, FakeRetriever, FakeLLM]:
    retriever = FakeRetriever(hits)
    llm = FakeLLM(VALID)
    pipeline = AskPipeline(_detecting(retriever), AnswerGenerator(llm), default_mode="vector")
    return pipeline, retriever, llm


@pytest.mark.parametrize(
    ("question", "notice"),
    [
        (
            "Was sagte Tamara Funiciello 2022?",
            "Zu diesem Zeitraum gibt es keine Daten. Die Voten reichen vom 4. Dezember 2023 bis "
            "2. Oktober 2026.",
        ),
        (
            "Qu'a dit le Conseil fédéral lors de la session d'hiver 2021 ?",
            "Il n'y a pas de données pour cette période. Les interventions vont du "
            "4 décembre 2023 au 2 octobre 2026.",
        ),
    ],
)
def test_out_of_range_answers_without_search_and_llm(question: str, notice: str) -> None:
    pipeline, retriever, llm = _pipeline([SPEECH])
    result = pipeline.ask(question)
    assert retriever.calls == [] and llm.calls == 0
    assert result.answer.insufficient_context
    assert result.answer.insufficient_reason == "out_of_range"
    assert result.answer.answer == notice
    assert result.answer.usage is None


def test_pipeline_reports_detection() -> None:
    pipeline, _, llm = _pipeline(HITS)
    result = pipeline.ask("Was sagte Bundesrat Rösti 2025 zum Winterstrom?")
    assert llm.calls == 1
    assert result.filters == year_2025(speaker="Rösti Albert")
    assert result.detected == ("speaker", "date_from", "date_to")
    assert result.coverage == Coverage(FIRST, LAST)
    assert result.retried_without == ()

    without = pipeline.ask("Was sagte Bundesrat Rösti 2025?", detect=False)
    assert without.filters == SearchFilters() and without.detected == ()


def test_answer_output_shows_detection_notes() -> None:
    pipeline, _, _ = _pipeline([_weak(SPEECH)])
    result = pipeline.ask("Was sagte Funiciello seit 2022 zum Winterstrom?")
    text = format_answer(result)
    assert "Aus der Frage erkannt: date_from=2022-01-01" in text
    assert "keine passenden Voten; gesucht wurde ohne Personenfilter" in text
    assert "Die Voten reichen vom 04.12.2023 bis 02.10.2026" in text
    payload = answer_payload(result)
    assert payload["detected"] == ["date_from"]
    assert payload["retried_without"] == ["speaker"]
    assert payload["coverage"] == {"first": "2023-12-04", "last": "2026-10-02", "partial": True}

    ambiguous = pipeline.ask("Was sagte Müller zur Stopfleber?")
    assert "Gemeint? Müller Damian (RL, BE) · Müller Leo (M-E, BE)" in format_answer(ambiguous)
    outside = format_answer(pipeline.ask("Was sagte Funiciello 2022?"))
    assert "Grund: Zeitraum ausserhalb der Daten" in outside


# --- Katalog-Cache --------------------------------------------------------------------------


def test_catalog_cache_reloads_after_ttl() -> None:
    now = [0.0]
    loads: list[int] = []

    def loader(_: Any) -> Catalog:
        loads.append(1)
        return CATALOG

    cache = CatalogCache(engine=None, ttl_s=600, clock=lambda: now[0], loader=loader)  # type: ignore[arg-type]
    assert cache.get() is CATALOG
    now[0] = 599
    cache.get()
    assert len(loads) == 1
    now[0] = 600
    cache.get()
    assert len(loads) == 2


def test_catalog_cache_survives_database_errors() -> None:
    now = [0.0]
    results: list[Catalog | Exception] = [OperationalError("x", {}, Exception()), CATALOG]

    def loader(_: Any) -> Catalog:
        result = results.pop(0) if results else OperationalError("x", {}, Exception())
        if isinstance(result, Exception):
            raise result
        return result

    cache = CatalogCache(engine=None, ttl_s=10, clock=lambda: now[0], loader=loader)  # type: ignore[arg-type]
    assert cache.get() == EMPTY_CATALOG  # ohne Datenbank: Suche ohne Erkennung
    now[0] = 10
    assert cache.get() is CATALOG
    now[0] = 20
    assert cache.get() is CATALOG  # Fehler beim Neuladen: letzter Katalog bleibt
