"""`parlrag ask` (Task 4.4): Pipeline und Ausgabe, ohne Modell, Datenbank und LLM."""

import dataclasses
import datetime as dt
import json
import uuid
from typing import Any

import pytest
from pydantic import BaseModel
from typer.testing import CliRunner

from fakes import FakeEmbedder
from parlrag import cli
from parlrag.generation import INSUFFICIENT_NOTICE, AnswerGenerator, AnswerOutput
from parlrag.generation.formatting import answer_payload, format_answer
from parlrag.generation.pipeline import AskPipeline, AskResult
from parlrag.llm import LLMConfigError, LLMError, LLMRefusalError, LLMResult, Usage
from parlrag.retrieval import SearchFilters, SearchHit

runner = CliRunner()

SPEECH = SearchHit(
    chunk_id=uuid.UUID(int=1),
    document_id=uuid.UUID(int=2),
    chunk_index=0,
    text="Wir brauchen den Strom vor allem im Winter. " * 8,
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
    url="https://www.parlament.ch/de/ratsbetrieb/amtliches-bulletin?SubjectId=82999#votum47",
    speaker_function="BR-M",
)
GROUP_SPEECH = dataclasses.replace(
    SPEECH,
    chunk_id=uuid.UUID(int=3),
    source_id="422495",
    text="Die Kernkraftwerke brauchen Kühlwasser aus der Aare.",
    speaker_name="Bregy Philipp Matthias",
    speaker_function=None,
    parl_group="M-E",
    canton="VS",
    url="https://www.parlament.ch/votum12",
)
HITS = [SPEECH, GROUP_SPEECH]


class FakeLLM:
    model = "claude-haiku-5-5"

    def __init__(self, output: AnswerOutput, backend: str = "api") -> None:
        self.output = output
        self.backend = backend
        self.calls = 0

    def generate[T: BaseModel](self, *, system: str, user: str, schema: type[T]) -> LLMResult[T]:
        self.calls += 1
        usage = Usage(
            model=self.model,
            input_tokens=2400,
            output_tokens=310,
            latency_ms=3100.0,
            cost_usd=0.00119,
            backend=self.backend,  # type: ignore[arg-type]
        )
        assert isinstance(self.output, schema)
        return LLMResult(output=self.output, usage=usage)


class FakeRetriever:
    def __init__(self, hits: list[SearchHit]) -> None:
        self.hits = hits
        self.calls: list[dict[str, Any]] = []
        self.embedder = FakeEmbedder()

    def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        *,
        mode: str = "hybrid",
        top_n: int | None = None,
    ) -> list[SearchHit]:
        self.calls.append({"query": query, "filters": filters, "mode": mode, "top_n": top_n})
        return self.hits


def _clock() -> Any:
    ticks = iter([1.0, 1.25, 4.25])
    return lambda: next(ticks)


VALID = AnswerOutput(
    answer="Rösti betonte den Winterstrom [1]. Bregy verwies auf das Kühlwasser [2].",
    citations=[1, 2],
    insufficient_context=False,
)


def _pipeline(
    output: AnswerOutput = VALID, hits: list[SearchHit] = HITS, backend: str = "api"
) -> tuple[AskPipeline, FakeRetriever, FakeLLM]:
    retriever = FakeRetriever(hits)
    llm = FakeLLM(output, backend)
    pipeline = AskPipeline(retriever, AnswerGenerator(llm), default_mode="vector", clock=_clock())
    return pipeline, retriever, llm


def test_pipeline_retrieves_then_answers_with_timings() -> None:
    pipeline, retriever, llm = _pipeline()
    filters = SearchFilters(council="NR")
    result = pipeline.ask("Was sagte Rösti zum Winterstrom?", filters)

    assert retriever.calls == [
        {
            "query": "Was sagte Rösti zum Winterstrom?",
            "filters": filters,
            "mode": "vector",
            "top_n": None,
        }
    ]
    assert llm.calls == 1
    assert result.mode == "vector" and result.filters == filters
    assert [s.number for s in result.answer.sources] == [1, 2]
    assert result.retrieval_ms == pytest.approx(250.0)
    assert result.generation_ms == pytest.approx(3000.0)
    assert result.total_ms == pytest.approx(3250.0)
    assert result.min_similarity == 0.55


def test_pipeline_mode_overrides_default() -> None:
    pipeline, retriever, _ = _pipeline()
    assert pipeline.ask("Frage?", mode="hybrid").mode == "hybrid"
    assert retriever.calls[0]["mode"] == "hybrid"


def test_warm_up_loads_embedder_only_for_vector_search() -> None:
    pipeline, retriever, _ = _pipeline()
    pipeline.clock = iter([0.0, 7.5]).__next__
    assert pipeline.warm_up() == pytest.approx(7500.0)
    assert pipeline.warm_up("fulltext") is None
    assert retriever.embedder.calls == 1


def test_build_pipeline_creates_llm_before_embedder(monkeypatch: pytest.MonkeyPatch) -> None:
    from parlrag.generation import pipeline as module

    def missing_key(settings: Any) -> None:
        raise LLMConfigError("ANTHROPIC_API_KEY fehlt.")

    def must_not_load(settings: Any) -> None:
        raise AssertionError("Embedding-Modell darf nicht vor dem LLM entstehen")

    monkeypatch.setattr(module, "get_llm", missing_key)
    monkeypatch.setattr(module, "get_embedder", must_not_load)
    with pytest.raises(LLMConfigError):
        module.build_pipeline(object())  # type: ignore[arg-type]


def _result(output: AnswerOutput = VALID, **options: Any) -> AskResult:
    pipeline, _, _ = _pipeline(output, **options)
    return pipeline.ask("Was sagte Rösti zum Winterstrom?", SearchFilters(council="NR"))


def test_format_answer_shows_answer_sources_and_usage() -> None:
    text = format_answer(_result(), model_load_ms=7100)
    lines = text.splitlines()

    assert lines[0] == "Frage «Was sagte Rösti zum Winterstrom?» · Filter council=NR"
    assert "Rösti betonte den Winterstrom [1]." in text
    assert "Quellen:" in lines
    assert "[1] Rösti Albert (Bundesrat) · Nationalrat · 30.09.2026 · 26.9022" in lines
    assert "[2] Bregy Philipp Matthias (M-E, VS) · Nationalrat · 30.09.2026 · 26.9022" in lines
    assert "    https://www.parlament.ch/votum12" in lines
    assert any(line.startswith("    «Wir brauchen den Strom") for line in lines)
    assert "claude-haiku-5-5 (api) · 2'400 Input- und 310 Output-Tokens · 0.0012 USD" in lines
    assert (
        "Suche 250 ms · LLM 3.0 s · gesamt 3.2 s (Embedding-Modell vorher geladen in 7.1 s)"
        in lines
    )


def test_subscription_cost_is_marked_as_estimate() -> None:
    text = format_answer(_result(backend="claude-code"))
    assert "(claude-code)" in text and "≈ 0.0012 USD geschätzt, im Claude-Abo enthalten" in text


def test_insufficient_context_shows_notice_and_reason_without_sources() -> None:
    low = [dataclasses.replace(hit, vector_similarity=0.48) for hit in HITS]
    text = format_answer(_result(hits=low))

    assert INSUFFICIENT_NOTICE["de"] in text
    assert "Quellen:" not in text
    assert "Grund: beste Similarity 0.48 unter der Schwelle 0.55 (kein LLM-Aufruf)." in text
    assert "Kein LLM-Aufruf." in text

    model = AnswerOutput(answer="Keine Antwort.", citations=[], insufficient_context=True)
    assert "Grund: Das Modell fand in den Quellen keine Antwort" in format_answer(_result(model))
    assert "Grund: Die Suche fand keine Treffer." in format_answer(_result(hits=[]))


def test_answer_payload() -> None:
    payload = answer_payload(_result(), model_load_ms=7100)

    assert payload["answer"].startswith("Rösti betonte")
    assert payload["insufficient_context"] is False and payload["insufficient_reason"] is None
    assert payload["filters"] == {"council": "NR"} and payload["mode"] == "vector"
    source = payload["sources"][0]
    assert source["number"] == 1 and source["source_key"] == "transcript:422528"
    assert source["speaker_name"] == "Rösti Albert" and source["date"] == "2026-09-30"
    assert source["url"].endswith("#votum47") and source["business_numbers"] == ["26.9022"]
    assert payload["usage"] == {
        "model": "claude-haiku-5-5",
        "backend": "api",
        "input_tokens": 2400,
        "output_tokens": 310,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "cost_usd": 0.00119,
        "cost_estimated": False,
        "latency_ms": 3100.0,
    }
    assert payload["timings"] == {
        "retrieval_ms": 250.0,
        "generation_ms": 3000.0,
        "total_ms": 3250.0,
        "model_load_ms": 7100.0,
    }
    assert payload["attempts"] == 1 and len(payload["prompt_version"]) == 12
    json.dumps(payload)  # serialisierbar


# --- CLI ---------------------------------------------------------------------------------


class FakePipeline:
    def __init__(self, result: AskResult | Exception) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []
        self.warmed: list[str | None] = []

    def warm_up(self, mode: str | None = None) -> float | None:
        self.warmed.append(mode)
        return None if mode == "fulltext" else 7100.0

    def ask(self, question: str, filters: SearchFilters, *, mode: str | None = None) -> AskResult:
        self.calls.append({"question": question, "filters": filters, "mode": mode})
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture
def fake_pipeline(monkeypatch: pytest.MonkeyPatch) -> FakePipeline:
    pipeline = FakePipeline(_result())
    monkeypatch.setattr(cli, "build_pipeline", lambda: pipeline)
    return pipeline


def test_ask_prints_answer_and_passes_options(fake_pipeline: FakePipeline) -> None:
    result = runner.invoke(
        cli.app,
        [
            "ask",
            "Was sagte Rösti zum Winterstrom?",
            "--council",
            "NR",
            "--date-from",
            "2026-09-01",
            "--parl-group",
            "M-E",
            "--mode",
            "hybrid",
        ],
    )

    assert result.exit_code == 0, result.output
    (call,) = fake_pipeline.calls
    assert call["mode"] == "hybrid" and fake_pipeline.warmed == ["hybrid"]
    assert call["filters"] == SearchFilters(
        council="NR", date_from=dt.date(2026, 9, 1), parl_group="M-E"
    )
    assert "Quellen:" in result.output and "https://www.parlament.ch/votum12" in result.output
    assert "Embedding-Modell vorher geladen in 7.1 s" in result.output


def test_ask_uses_configured_mode_by_default(fake_pipeline: FakePipeline) -> None:
    runner.invoke(cli.app, ["ask", "Frage?"])
    assert fake_pipeline.calls[0]["mode"] is None and fake_pipeline.warmed == [None]


def test_ask_json(fake_pipeline: FakePipeline) -> None:
    result = runner.invoke(cli.app, ["ask", "Frage?", "--json"])
    payload = json.loads(result.output)
    assert payload["sources"][1]["source_key"] == "transcript:422495"
    assert payload["timings"]["model_load_ms"] == 7100.0


@pytest.mark.parametrize(
    "error",
    [
        LLMConfigError("ANTHROPIC_API_KEY fehlt. Den Key in .env eintragen."),
        LLMRefusalError("Anfrage abgelehnt (Kategorie: unbekannt)."),
        LLMError("Limit des Claude-Abos erreicht (429)."),
    ],
)
def test_ask_errors_exit_with_message(monkeypatch: pytest.MonkeyPatch, error: LLMError) -> None:
    monkeypatch.setattr(cli, "build_pipeline", lambda: FakePipeline(error))
    result = runner.invoke(cli.app, ["ask", "Frage?"])

    assert result.exit_code == 1
    assert str(error).split(" (")[0].split(".")[0] in result.output
    assert "Traceback" not in result.output


def test_ask_reports_missing_configuration_before_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing() -> None:
        raise LLMConfigError("Claude Code CLI (`claude`) nicht gefunden.")

    monkeypatch.setattr(cli, "build_pipeline", missing)
    result = runner.invoke(cli.app, ["ask", "Frage?"])
    assert result.exit_code == 1 and "nicht gefunden" in result.output


def test_ask_rejects_invalid_date_range(fake_pipeline: FakePipeline) -> None:
    result = runner.invoke(
        cli.app, ["ask", "Frage?", "--date-from", "2026-09-30", "--date-to", "2026-09-01"]
    )
    assert result.exit_code == 2 and fake_pipeline.calls == []


def test_usage_line_counts_cached_prompt_tokens() -> None:
    from parlrag.generation.formatting import usage_line

    usage = Usage(
        model="claude-haiku-5-5",
        input_tokens=2,
        output_tokens=896,
        cache_creation_input_tokens=25364,
        cost_usd=0.0018,
        backend="claude-code",
    )
    assert usage_line(usage, attempts=2) == (
        "claude-haiku-5-5 (claude-code) · 25'366 Input- (davon 25'364 Cache) und 896 "
        "Output-Tokens · ≈ 0.0018 USD geschätzt, im Claude-Abo enthalten · 2 Versuche"
    )
