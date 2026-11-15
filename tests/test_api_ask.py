"""`POST /ask` (Task 5.1): Antwort, Quellen, Usage, Fehler und Logging, mit Fake-Pipeline."""

import dataclasses
import datetime as dt
import logging
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from parlrag.api.ask import pipeline_provider
from parlrag.api.main import app
from parlrag.generation import INSUFFICIENT_NOTICE, CitedSource, GeneratedAnswer
from parlrag.generation.pipeline import AskResult
from parlrag.llm import (
    LLMConfigError,
    LLMError,
    LLMOutputError,
    LLMRefusalError,
    Usage,
)
from parlrag.retrieval import SearchFilters, SearchHit

HIT = SearchHit(
    chunk_id=uuid.UUID(int=1),
    document_id=uuid.UUID(int=2),
    chunk_index=0,
    text="Wir brauchen den Strom vor allem im Winter.",
    section=None,
    score=0.016,
    rank=1,
    fulltext_rank=None,
    fulltext_score=None,
    vector_rank=1,
    vector_similarity=0.70,
    source_type="transcript",
    source_id="422528",
    language="de",
    title="26.9022 Aktuelle Debatte. Hitzewelle und Dürre",
    speaker_name="Rösti Albert",
    parl_group=None,
    canton="BE",
    council="NR",
    date=dt.date(2026, 9, 30),
    debate_dates=(),
    debate_councils=(),
    business_numbers=("26.9022",),
    url="https://www.parlament.ch/votum47",
    speaker_function="BR-M",
)
QUESTION = "Was sagte Bundesrat Rösti zum Winterstrom?"


def _answer(**changes: Any) -> GeneratedAnswer:
    base = GeneratedAnswer(
        answer="Rösti betonte den Winterstrom [1].",
        insufficient_context=False,
        sources=[CitedSource(number=1, hit=HIT)],
        context=[HIT],
        usage=Usage(
            model="claude-opus-5-5",
            input_tokens=2400,
            output_tokens=310,
            cache_read_input_tokens=100,
            latency_ms=3100.0,
            cost_usd=0.0161,
        ),
        attempts=1,
        prompt_version="abc",
        best_similarity=0.70,
    )
    return dataclasses.replace(base, **changes)


class FakePipeline:
    def __init__(self, result: GeneratedAnswer | Exception) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def ask(
        self, question: str, filters: SearchFilters | None = None, *, mode: str | None = None
    ) -> AskResult:
        self.calls.append({"question": question, "filters": filters, "mode": mode})
        if isinstance(self.result, Exception):
            raise self.result
        return AskResult(
            question=question,
            filters=filters or SearchFilters(),
            mode="vector",
            answer=self.result,
            hits=[HIT],
            min_similarity=0.55,
            retrieval_ms=300.0,
            generation_ms=3000.0,
        )


@pytest.fixture
def api() -> Iterator[dict[str, Any]]:
    state: dict[str, Any] = {"pipeline": FakePipeline(_answer()), "built": 0}

    def provider() -> Any:
        def build() -> Any:
            state["built"] += 1
            if isinstance(state["pipeline"], Exception):
                raise state["pipeline"]
            return state["pipeline"]

        return build

    app.dependency_overrides[pipeline_provider] = provider
    state["client"] = TestClient(app)
    yield state
    app.dependency_overrides.clear()


def test_ask_returns_answer_sources_and_usage(api: dict[str, Any]) -> None:
    response = api["client"].post("/ask", json={"question": QUESTION})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["answer"] == "Rösti betonte den Winterstrom [1]."
    assert body["insufficient_context"] is False and body["insufficient_reason"] is None
    (source,) = body["sources"]
    assert source == {
        "number": 1,
        "source_key": "transcript:422528",
        "source_type": "transcript",
        "language": "de",
        "title": "26.9022 Aktuelle Debatte. Hitzewelle und Dürre",
        "speaker_name": "Rösti Albert",
        "speaker_function": "BR-M",
        "parl_group": None,
        "canton": "BE",
        "council": "NR",
        "date": "2026-09-30",
        "business_numbers": ["26.9022"],
        "section": None,
        "text": "Wir brauchen den Strom vor allem im Winter.",
        "url": "https://www.parlament.ch/votum47",
    }
    usage = body["usage"]
    assert usage["model"] == "claude-opus-5-5" and usage["backend"] == "api"
    assert (usage["input_tokens"], usage["output_tokens"]) == (2500, 310)  # Input inkl. Cache
    assert usage["cost_usd"] == 0.0161 and usage["cost_estimated"] is False
    assert usage["latency_ms"] >= 0
    assert len(response.headers["X-Request-ID"]) == 12


def test_filters_are_passed_to_the_pipeline(api: dict[str, Any]) -> None:
    filters = {"council": "SR", "date_from": "2026-09-01", "parl_group": "RL"}
    response = api["client"].post("/ask", json={"question": QUESTION, "filters": filters})

    assert response.status_code == 200
    (call,) = api["pipeline"].calls
    assert call["filters"] == SearchFilters(
        council="SR", date_from=dt.date(2026, 9, 1), parl_group="RL"
    )
    assert call["question"] == QUESTION


def test_insufficient_context_without_llm_call(api: dict[str, Any]) -> None:
    api["pipeline"] = FakePipeline(
        _answer(
            answer=INSUFFICIENT_NOTICE["de"],
            insufficient_context=True,
            sources=[],
            usage=None,
            attempts=0,
            insufficient_reason="low_similarity",
        )
    )
    body = api["client"].post("/ask", json={"question": QUESTION}).json()

    assert body["answer"] == INSUFFICIENT_NOTICE["de"] and body["sources"] == []
    assert body["insufficient_context"] is True and body["insufficient_reason"] == "low_similarity"
    assert body["usage"]["model"] is None and body["usage"]["cost_usd"] == 0.0
    assert body["usage"]["input_tokens"] == 0


def test_subscription_cost_is_marked_as_estimate(api: dict[str, Any]) -> None:
    subscription = Usage(
        model="claude-haiku-5-5",
        input_tokens=2,
        output_tokens=900,
        cost_usd=0.002,
        cache_creation_input_tokens=9000,
        backend="claude-code",
    )
    api["pipeline"] = FakePipeline(_answer(usage=subscription))
    usage = api["client"].post("/ask", json={"question": QUESTION}).json()["usage"]
    assert usage["cost_estimated"] is True and usage["input_tokens"] == 9002


@pytest.mark.parametrize(
    "payload",
    [
        {"question": "ab"},
        {"question": "x" * 501},
        {},
        {"question": QUESTION, "filters": {"council": "XX"}},
        {"question": QUESTION, "filters": {"date_from": "2026-09-30", "date_to": "2026-09-01"}},
        {"question": QUESTION, "extra": 1},
    ],
)
def test_invalid_requests_are_rejected(api: dict[str, Any], payload: dict[str, Any]) -> None:
    response = api["client"].post("/ask", json=payload)
    assert response.status_code == 422
    assert api["pipeline"].calls == []


@pytest.mark.parametrize(
    ("error", "http_status", "message"),
    [
        (
            LLMConfigError("ANTHROPIC_API_KEY fehlt."),
            503,
            "LLM nicht verfügbar: ANTHROPIC_API_KEY fehlt.",
        ),
        (LLMRefusalError("abgelehnt"), 422, "Das Modell hat die Anfrage abgelehnt."),
        (LLMOutputError("Zitatregeln verletzt"), 502, "Das Modell lieferte keine gültige Antwort."),
        (LLMError("Limit (429)"), 503, "LLM vorübergehend nicht verfügbar: Limit (429)"),
    ],
)
def test_llm_errors_become_clear_http_errors(
    api: dict[str, Any], error: LLMError, http_status: int, message: str
) -> None:
    api["pipeline"] = FakePipeline(error)
    response = api["client"].post("/ask", json={"question": QUESTION})

    assert response.status_code == http_status
    assert response.json() == {"detail": message}
    assert "X-Request-ID" in response.headers


def test_configuration_error_while_building_the_pipeline(api: dict[str, Any]) -> None:
    api["pipeline"] = LLMConfigError("Claude Code CLI (`claude`) nicht gefunden.")
    response = api["client"].post("/ask", json={"question": QUESTION})
    assert response.status_code == 503 and "nicht gefunden" in response.json()["detail"]


def test_request_is_logged_with_usage_but_without_question(
    api: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="parlrag.api"):
        response = api["client"].post(
            "/ask", json={"question": QUESTION, "filters": {"council": "NR"}}
        )

    (line,) = [r.getMessage() for r in caplog.records if r.name == "parlrag.api"]
    request_id = response.headers["X-Request-ID"]
    assert line.startswith(f"ask_request request_id={request_id} status=200 ")
    for part in (
        f"question_chars={len(QUESTION)}",
        "language=de",
        "filters=council=NR",
        "insufficient=False",
        "sources=1",
        "model=claude-opus-5-5",
        "input_tokens=2500",
        "output_tokens=310",
        "cost_usd=0.016100",
    ):
        assert part in line, part
    assert "Rösti" not in line and "Winterstrom" not in line  # kein Wortlaut der Frage


def test_failed_request_is_logged(api: dict[str, Any], caplog: pytest.LogCaptureFixture) -> None:
    api["pipeline"] = FakePipeline(LLMError("Limit (429)"))
    with caplog.at_level(logging.INFO, logger="parlrag.api"):
        api["client"].post("/ask", json={"question": QUESTION})
    (line,) = [r.getMessage() for r in caplog.records if r.name == "parlrag.api"]
    assert "status=503" in line and "error=LLMError" in line


def test_pipeline_is_built_once_per_process(monkeypatch: pytest.MonkeyPatch) -> None:
    from parlrag.api import ask as module

    built: list[int] = []

    def build() -> FakePipeline:
        built.append(1)
        return FakePipeline(_answer())

    monkeypatch.setattr(module, "build_pipeline", build)
    module.get_pipeline.cache_clear()
    try:
        client = TestClient(app)
        client.post("/ask", json={"question": QUESTION})
        client.post("/ask", json={"question": QUESTION})
        assert built == [1]
    finally:
        module.get_pipeline.cache_clear()


def test_openapi_documents_ask() -> None:
    schema = TestClient(app).get("/openapi.json").json()
    assert "/ask" in schema["paths"] and "post" in schema["paths"]["/ask"]
