"""Antwort-Evals (Task 4.5a): Judge, Metriken, Ergebnisdateien und `parlrag eval --answers`.

Ohne LLM, Modell und Datenbank: Fake-Pipeline und Fake-Judge-LLM mit festen Antworten.
"""

import dataclasses
import datetime as dt
import json
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel
from typer.testing import CliRunner

from fakes import FakeEmbedder
from parlrag import cli
from parlrag.evals import GoldenItem
from parlrag.evals.answers import (
    AnswerResult,
    count_answers,
    evaluate_answer,
    evaluate_answers,
    resume_mismatch,
    reusable_answers,
    summarize_answers,
)
from parlrag.evals.judge import (
    CitationVerdict,
    Judge,
    JudgeOutput,
    StatementVerdict,
    build_judge_message,
    citation_accuracy,
    faithfulness,
)
from parlrag.evals.results import (
    EvalRun,
    answer_progress,
    answer_rows,
    find_previous,
    load_run,
    metric_rows,
    render_markdown,
    run_stem,
    write_run,
)
from parlrag.generation import INSUFFICIENT_NOTICE, CitedSource, GeneratedAnswer
from parlrag.generation.pipeline import AskResult
from parlrag.llm import LLMError, LLMResult, Usage
from parlrag.prompts import load_prompt
from parlrag.retrieval import RetrievalConfig, SearchFilters, SearchHit

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
    source_id="1",
    language="de",
    title="26.9022 Aktuelle Debatte",
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
OTHER = dataclasses.replace(HIT, chunk_id=uuid.UUID(int=3), source_id="9", text="Anderes Thema.")

ITEMS = [
    GoldenItem.model_validate(item)
    for item in [
        {
            "id": "q01",
            "question": "Was sagte Bundesrat Rösti zum Winterstrom?",
            "language": "de",
            "expected_source_ids": ["transcript:1"],
            "answerable": True,
            "tags": ["smoke"],
        },
        {
            "id": "q02",
            "question": "Qu'a dit le Conseil fédéral sur l'hiver ?",
            "language": "fr",
            "expected_source_ids": ["transcript:1"],
            "answerable": True,
            "tags": ["fr", "crosslingual", "smoke"],
        },
        {
            "id": "q03",
            "question": "Was beschloss der Bieler Stadtrat zur Fusion?",
            "language": "de",
            "expected_source_ids": [],
            "answerable": False,
            "tags": ["unanswerable", "smoke"],
        },
        {
            "id": "q04",
            "question": "Ist die Vorlage gut für die Schweiz?",
            "language": "de",
            "expected_source_ids": ["transcript:1"],
            "answerable": True,
            "tags": ["wertend", "smoke"],
        },
    ]
]


def _usage(cost: float | None = 0.002, backend: str = "api") -> Usage:
    return Usage(
        model="claude-haiku-5-5",
        input_tokens=2000,
        output_tokens=300,
        cost_usd=cost,
        backend=backend,  # type: ignore[arg-type]
    )


def _answered(text: str, cited: list[SearchHit], cost: float | None = 0.002) -> GeneratedAnswer:
    return GeneratedAnswer(
        answer=text,
        insufficient_context=False,
        sources=[CitedSource(number=n, hit=hit) for n, hit in enumerate(cited, start=1)],
        context=[HIT, OTHER],
        usage=_usage(cost),
        attempts=1,
        prompt_version="abc",
        best_similarity=0.7,
    )


def _refused(question_language: str = "de") -> GeneratedAnswer:
    return GeneratedAnswer(
        answer=INSUFFICIENT_NOTICE[question_language],
        insufficient_context=True,
        sources=[],
        context=[],
        usage=None,
        attempts=0,
        prompt_version="abc",
        insufficient_reason="low_similarity",
        best_similarity=0.48,
    )


ANSWERS = {
    "q01": _answered("Rösti sagte, man brauche den Strom vor allem im Winter [1].", [HIT]),
    "q02": _answered(
        "Le Conseil fédéral a dit que l'électricité est surtout nécessaire en hiver [1].", [HIT]
    ),
    "q03": _refused(),
    "q04": _answered("Die Vorlage ist gut für die Schweiz [1].", [HIT]),
}


class FakePipeline:
    def __init__(self, answers: Mapping[str, GeneratedAnswer | Exception] | None = None) -> None:
        self.answers = answers if answers is not None else dict(ANSWERS)
        self.calls: list[dict[str, Any]] = []

    def ask(
        self, question: str, filters: SearchFilters | None = None, *, mode: str | None = None
    ) -> AskResult:
        self.calls.append({"question": question, "filters": filters, "mode": mode})
        item = next(item for item in ITEMS if item.question == question)
        answer = self.answers[item.id]
        if isinstance(answer, Exception):
            raise answer
        return AskResult(
            question=question,
            filters=filters or SearchFilters(),
            mode="vector",
            answer=answer,
            hits=[HIT, OTHER],
            min_similarity=0.55,
            retrieval_ms=300.0,
            generation_ms=2700.0 if not answer.insufficient_context else 0.0,
        )


def _verdict(support: str = "supported", own: bool = False, supports: bool = True) -> JudgeOutput:
    return JudgeOutput(
        statements=[
            StatementVerdict(
                statement="Aussage",
                citations=[CitationVerdict(number=1, supports=supports)],
                support=support,  # type: ignore[arg-type]
            )
        ],
        contains_own_evaluation=own,
        evaluation_note="«ist gut»" if own else "",
    )


class FakeJudgeLLM:
    model = "claude-sonnet-5-5"

    def __init__(self, verdicts: dict[str, JudgeOutput | Exception] | None = None) -> None:
        self.verdicts = verdicts or {}
        self.calls: list[dict[str, Any]] = []

    def generate[T: BaseModel](self, *, system: str, user: str, schema: type[T]) -> LLMResult[T]:
        self.calls.append({"system": system, "user": user, "schema": schema})
        question = user.split("\n\n")[1]
        item = next(item for item in ITEMS if item.question == question)
        verdict = self.verdicts.get(item.id, _verdict(own=item.has("wertend")))
        if isinstance(verdict, Exception):
            raise verdict
        assert isinstance(verdict, schema)
        return LLMResult(output=verdict, usage=_usage(0.004))


# --- Judge -------------------------------------------------------------------------------


def test_citation_accuracy_and_faithfulness() -> None:
    output = JudgeOutput(
        statements=[
            StatementVerdict(
                statement="A",
                citations=[
                    CitationVerdict(number=1, supports=True),
                    CitationVerdict(number=2, supports=False),
                ],
                support="supported",
            ),
            StatementVerdict(
                statement="B",
                citations=[CitationVerdict(number=3, supports=True)],
                support="partial",
            ),
            StatementVerdict(statement="C", citations=[], support="unsupported"),
        ],
        contains_own_evaluation=False,
        evaluation_note="",
    )
    assert citation_accuracy(output) == pytest.approx(2 / 3)
    assert faithfulness(output) == pytest.approx((1 + 0.5 + 0) / 3)
    empty = JudgeOutput(statements=[], contains_own_evaluation=False, evaluation_note="")
    assert citation_accuracy(empty) is None and faithfulness(empty) is None


def test_judge_message_and_prompt() -> None:
    message = build_judge_message("Frage?", [HIT, OTHER], "Antwort [1].")
    assert message.startswith("Frage:\n\nFrage?\n\nQuellen:\n\n[1] Nationalrat · 30.09.2026")
    assert "\n\n[2] " in message and message.endswith("Antwort:\n\nAntwort [1].")

    llm = FakeJudgeLLM()
    judge = Judge(llm)
    verdict, usage = judge.judge(ITEMS[0].question, [HIT], "Antwort [1].")
    assert verdict == _verdict() and usage.cost_usd == 0.004
    assert llm.calls[0]["system"] == load_prompt("judge").text
    assert llm.calls[0]["schema"] is JudgeOutput
    assert judge.model == "claude-sonnet-5-5"

    prompt = load_prompt("judge").text
    for rule in ("nur anhand der Quellen", "`supported`", "`partial`", "contains_own_evaluation"):
        assert rule in prompt, rule


# --- Einzelne Fragen ---------------------------------------------------------------------


def test_answered_question_is_judged() -> None:
    result = evaluate_answer(ITEMS[0], FakePipeline(), Judge(FakeJudgeLLM()), "vector")

    assert result.ok and not result.refused
    assert result.sources == ["[1] transcript:1"] and result.cited_expected == ["transcript:1"]
    assert result.answer_language == "de" and result.language_ok
    assert result.citation_accuracy == 1.0 and result.faithfulness == 1.0 and result.neutral
    assert result.total_ms == pytest.approx(3000.0)
    assert result.answer_usage is not None and result.answer_usage["cost_usd"] == 0.002
    assert result.judge_usage is not None and result.judge_usage["cost_usd"] == 0.004


def test_refused_question_is_not_judged() -> None:
    llm = FakeJudgeLLM()
    result = evaluate_answer(ITEMS[2], FakePipeline(), Judge(llm), "vector")

    assert result.refused and result.insufficient_reason == "low_similarity"
    assert result.neutral is True and result.judge is None and llm.calls == []
    assert result.answer_usage is None


def test_pipeline_error_is_recorded() -> None:
    error = LLMError("Limit des Claude-Abos erreicht (429).", _usage(0.001))
    result = evaluate_answer(
        ITEMS[0], FakePipeline({"q01": error}), Judge(FakeJudgeLLM()), "vector"
    )
    assert not result.ok and "429" in (result.error or "")
    assert result.answer_usage is not None and result.answer_usage["cost_usd"] == 0.001


def test_judge_error_is_recorded() -> None:
    llm = FakeJudgeLLM({"q01": LLMError("Judge kaputt")})
    result = evaluate_answer(ITEMS[0], FakePipeline(), Judge(llm), "vector")
    assert result.ok and result.judge is None and result.judge_error == "Judge kaputt"
    assert result.citation_accuracy is None


# --- Metriken ----------------------------------------------------------------------------


def _report(**options: Any) -> Any:
    return evaluate_answers(
        ITEMS,
        options.get("pipeline", FakePipeline()),
        Judge(options.get("llm", FakeJudgeLLM())),
        "vector",
    )


def test_answer_metrics() -> None:
    report = _report()
    metrics = report.metrics

    assert metrics["citation_accuracy"] == 1.0
    assert metrics["faithfulness"] == 1.0
    assert metrics["refusal_rate"] == 1.0  # q03 abgelehnt
    assert metrics["false_refusal_rate"] == 0.0  # q01, q02 beantwortet; q04 wertend zählt nicht
    assert metrics["neutrality"] == 0.0  # q04 wertet selbst
    assert metrics["language_accuracy"] == 1.0
    assert metrics["answer_p95_ms"] == pytest.approx(3000.0)
    assert metrics["answer_cost_usd"] == pytest.approx((0.002 * 3 + 0.0) / 4)
    assert metrics["judge_cost_usd"] == pytest.approx(0.004)
    assert report.counts == {
        "questions": 4,
        "answered": 3,
        "refused": 1,
        "judged": 3,
        "errors": 0,
        "judge_errors": 0,
    }


def test_false_refusals_and_wrong_language() -> None:
    answers = dict(ANSWERS)
    answers["q01"] = _refused()
    answers["q02"] = _answered("Der Bundesrat sagte, der Strom fehle im Winter [1].", [HIT])
    answers["q03"] = _answered("Der Stadtrat beschloss die Fusion [1].", [OTHER])
    answers["q04"] = _refused()
    metrics = _report(pipeline=FakePipeline(answers)).metrics

    assert metrics["false_refusal_rate"] == 0.5
    assert metrics["refusal_rate"] == 0.0
    assert metrics["neutrality"] == 1.0  # Ablehnung einer wertenden Frage ist neutral
    assert metrics["language_accuracy"] == pytest.approx(3 / 4)  # q02 deutsch statt französisch


def test_partial_support_and_wrong_citation() -> None:
    llm = FakeJudgeLLM({"q01": _verdict("partial", supports=False)})
    metrics = _report(llm=llm).metrics
    assert metrics["citation_accuracy"] == pytest.approx(2 / 3)
    assert metrics["faithfulness"] == pytest.approx((0.5 + 1 + 1) / 3)


def test_errors_are_excluded_and_unknown_cost_is_omitted() -> None:
    answers: dict[str, Any] = dict(ANSWERS)
    answers["q01"] = LLMError("Limit (429)")
    answers["q02"] = _answered("Le Conseil fédéral parle de l'hiver [1].", [HIT], cost=None)
    report = _report(pipeline=FakePipeline(answers))

    assert report.counts["errors"] == 1
    assert "answer_cost_usd" not in report.metrics  # eine Antwort ohne Kosten
    assert report.metrics["false_refusal_rate"] == 0.0  # nur q02 gezählt


def test_summarize_without_answers() -> None:
    assert summarize_answers([]) == {}
    assert count_answers([])["questions"] == 0


# --- Ergebnisdateien ---------------------------------------------------------------------


def _run(
    answers: list[AnswerResult] | None = None,
    model: str = "claude-haiku-5-5",
    created: dt.datetime = dt.datetime(2026, 11, 14, 10, 0, tzinfo=dt.UTC),
) -> EvalRun:
    answer_list = answers if answers is not None else _report().answers
    return EvalRun(
        created_at=created,
        git_sha="abc1234def",
        git_dirty=False,
        suite="smoke",
        mode="vector",
        golden="evals/datasets/golden.jsonl",
        questions_total=4,
        skipped_unanswerable=1,
        config={},
        corpus={},
        metrics=summarize_answers(answer_list),
        subsets={},
        questions=[],
        answer_config={
            "answer_model": model,
            "answer_effort": "low",
            "judge_model": "claude-sonnet-5-5",
            "judge_effort": "medium",
            "llm_backend": "claude-code",
        },
        answer_counts=count_answers(answer_list),
        answers=answer_list,
    )


def test_answer_runs_have_their_own_files_and_previous(tmp_path: Path) -> None:
    run = _run()
    assert run_stem(run) == "2026-11-14_abc1234_smoke-vector-answers"
    write_run(run, None, tmp_path)
    write_run(
        _run(model="claude-opus-5-5", created=run.created_at + dt.timedelta(hours=1)),
        None,
        tmp_path,
    )

    haiku = find_previous(tmp_path, "smoke", "vector", "claude-haiku-5-5")
    assert haiku is not None and load_run(haiku).answer_model == "claude-haiku-5-5"
    assert find_previous(tmp_path, "smoke", "vector") is None  # kein Lauf ohne Antworten
    assert load_run(haiku).answers[0].judge is not None


def test_metric_rows_format_answer_metrics() -> None:
    rows = {row[0]: row[1:] for row in metric_rows(_run().metrics, None)}
    assert rows["Zitiergenauigkeit"] == ("1.000", "-", "-")
    assert rows["Antwortzeit p95"] == ("3000 ms", "-", "-")
    assert rows["Kosten Antwort pro Frage"] == ("0.0015 USD", "-", "-")
    previous = {"answer_cost_usd": 0.0025, "refusal_rate": 0.5}
    rows = {row[0]: row[1:] for row in metric_rows(_run().metrics, previous)}
    assert rows["Kosten Antwort pro Frage"][2] == "-0.0010 USD"
    assert rows["Ablehnungsquote (unbeantwortbar)"][2] == "+0.500"
    assert "Zitiergenauigkeit" not in {row[0] for row in metric_rows({"recall@10": 1.0}, None)}


def test_markdown_and_rows_for_answers() -> None:
    run = _run()
    rows = {row[0]: row for row in answer_rows(run)}
    assert rows["q01"][1:5] == ("de", "beantwortet", "1", "1.000")
    assert rows["q03"][2] == "abgelehnt (Schwelle)" and rows["q03"][3] == "-"
    assert rows["q04"][1] == "wertend" and rows["q04"][7] == "nein"

    text = render_markdown(run, None)
    assert "## Antworten" in text
    assert "4 Fragen: 3 beantwortet, 1 abgelehnt, 0 Fehler; 3 vom Judge bewertet." in text
    assert "Antwortzeiten enthalten den Start der CLI" in text
    assert answer_progress(run.answers[0]).startswith("q01  beantwortet  Zitate 1.00")


def test_old_result_files_without_answers_still_load(tmp_path: Path) -> None:
    data = json.loads(_run().model_dump_json())
    for key in ("answer_config", "answer_counts", "answers"):
        del data[key]
    path = tmp_path / "alt.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    old = load_run(path)
    assert old.answers == [] and old.answer_model is None


# --- CLI ---------------------------------------------------------------------------------

runner = CliRunner()


class FakeRetriever:
    def __init__(self) -> None:
        self.embedder = FakeEmbedder()
        self.config = RetrievalConfig()

    def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        *,
        mode: str = "hybrid",
        top_n: int | None = None,
    ) -> list[SearchHit]:
        return [HIT, OTHER]


@pytest.fixture
def cli_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    golden = tmp_path / "golden.jsonl"
    golden.write_text(
        "\n".join(item.model_dump_json(exclude_none=True) for item in ITEMS) + "\n",
        encoding="utf-8",
    )
    pipeline = FakePipeline()
    built: list[Any] = []

    def build(retriever: Any) -> tuple[Any, Judge, dict[str, Any]]:
        built.append(retriever)
        return (
            pipeline,
            Judge(FakeJudgeLLM()),
            {"answer_model": "claude-haiku-5-5", "llm_backend": "api"},
        )

    monkeypatch.setattr(cli, "git_state", lambda: ("abc1234def", False))
    monkeypatch.setattr(cli, "build_retriever", FakeRetriever)
    monkeypatch.setattr(cli, "describe_eval", lambda r: ({}, {"documents": 1, "chunks": 2}))
    monkeypatch.setattr(cli, "build_answer_evaluation", build)
    return {
        "args": ["--golden", str(golden), "--results-dir", str(tmp_path / "results")],
        "results": tmp_path / "results",
        "pipeline": pipeline,
        "built": built,
    }


def test_eval_with_answers(cli_env: dict[str, Any]) -> None:
    result = runner.invoke(cli.app, ["eval", "--answers", *cli_env["args"]])

    assert result.exit_code == 0, result.output
    assert len(cli_env["pipeline"].calls) == 4  # smoke: alle vier, auch unbeantwortbar
    assert isinstance(cli_env["built"][0], FakeRetriever)  # Retriever geteilt
    assert "Zitiergenauigkeit" in result.output and "q03  abgelehnt (Schwelle)" in result.output
    (path,) = cli_env["results"].glob("*.json")
    assert path.name.endswith("smoke-vector-answers.json")
    run = load_run(path)
    assert run.metrics["refusal_rate"] == 1.0 and "recall@10" in run.metrics
    assert run.answer_counts["answered"] == 3 and len(run.answers) == 4


def test_eval_without_answers_makes_no_llm_calls(cli_env: dict[str, Any]) -> None:
    result = runner.invoke(cli.app, ["eval", *cli_env["args"]])
    assert result.exit_code == 0, result.output
    assert cli_env["pipeline"].calls == [] and cli_env["built"] == []
    (path,) = cli_env["results"].glob("*.json")
    assert not path.name.endswith("-answers.json")


def test_eval_answers_stops_early_on_configuration_error(
    cli_env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def missing(retriever: Any) -> None:
        raise LLMError("ANTHROPIC_API_KEY fehlt.")

    monkeypatch.setattr(cli, "build_answer_evaluation", missing)
    result = runner.invoke(cli.app, ["eval", "--answers", *cli_env["args"]])
    assert result.exit_code == 1 and "ANTHROPIC_API_KEY fehlt" in result.output
    assert not cli_env["results"].exists()


# --- Abo-Limits: früher Abbruch und Fortsetzen (Task 4.5b) -------------------------------


def test_consecutive_errors_skip_remaining_questions() -> None:
    error = LLMError("Limit des Claude-Abos erreicht (429)")
    pipeline = FakePipeline({item.id: error for item in ITEMS})
    report = evaluate_answers(
        ITEMS, pipeline, Judge(FakeJudgeLLM()), "vector", max_consecutive_errors=2
    )

    assert len(pipeline.calls) == 2  # q03 und q04 ohne Aufruf
    assert [(a.error or "").startswith("Übersprungen nach 2 Fehlern") for a in report.answers] == [
        False,
        False,
        True,
        True,
    ]
    assert report.counts["errors"] == 4


def test_a_success_resets_the_error_counter() -> None:
    answers: dict[str, Any] = dict(ANSWERS)
    answers["q01"] = LLMError("Limit (429)")
    answers["q03"] = LLMError("Limit (429)")
    pipeline = FakePipeline(answers)
    evaluate_answers(ITEMS, pipeline, Judge(FakeJudgeLLM()), "vector", max_consecutive_errors=2)
    assert len(pipeline.calls) == 4


def test_reuse_skips_answered_questions() -> None:
    first = _report()
    failed = first.answers[1].model_copy(update={"error": "Limit (429)"})
    judge_failed = first.answers[3].model_copy(update={"judge_error": "kaputt"})
    previous = [first.answers[0], failed, first.answers[2], judge_failed]

    reuse = reusable_answers(previous, ITEMS)
    assert set(reuse) == {"q01", "q03"}
    assert set(reusable_answers(previous, ITEMS[:1])) == {"q01"}  # nur aktuelle Auswahl

    pipeline = FakePipeline()
    report = evaluate_answers(ITEMS, pipeline, Judge(FakeJudgeLLM()), "vector", reuse=reuse)
    assert [call["question"] for call in pipeline.calls] == [ITEMS[1].question, ITEMS[3].question]
    assert report.answers[0] is reuse["q01"] and report.counts["errors"] == 0


def test_resume_mismatch() -> None:
    config = {"answer_model": "claude-haiku-5-5", "answer_prompt_version": "abc"}
    assert resume_mismatch(config, dict(config)) == []
    assert resume_mismatch(config, config | {"answer_prompt_version": "def"}) == [
        "answer_prompt_version"
    ]
    assert "answer_model" in resume_mismatch(None, config)


def test_eval_resume_takes_over_answers(cli_env: dict[str, Any]) -> None:
    first = runner.invoke(cli.app, ["eval", "--answers", *cli_env["args"]])
    assert first.exit_code == 0, first.output
    (path,) = cli_env["results"].glob("*.json")
    run = load_run(path)
    broken = run.model_copy(
        update={
            "answers": [
                run.answers[0].model_copy(update={"error": "Limit (429)"}),
                *run.answers[1:],
            ]
        }
    )
    path.write_text(broken.model_dump_json(), encoding="utf-8")
    cli_env["pipeline"].calls.clear()

    result = runner.invoke(cli.app, ["eval", "--answers", "--resume", str(path), *cli_env["args"]])

    assert result.exit_code == 0, result.output
    assert "Übernehme 3 fehlerfreie Antworten" in result.output
    assert [call["question"] for call in cli_env["pipeline"].calls] == [ITEMS[0].question]


def test_eval_resume_rejects_other_configuration(cli_env: dict[str, Any]) -> None:
    runner.invoke(cli.app, ["eval", "--answers", *cli_env["args"]])
    (path,) = cli_env["results"].glob("*.json")
    run = load_run(path)
    other = run.model_copy(
        update={"answer_config": {**(run.answer_config or {}), "answer_model": "x"}}
    )
    path.write_text(other.model_dump_json(), encoding="utf-8")

    result = runner.invoke(cli.app, ["eval", "--answers", "--resume", str(path), *cli_env["args"]])
    assert result.exit_code == 1 and "answer_model" in result.output
    no_answers = runner.invoke(cli.app, ["eval", "--resume", str(path), *cli_env["args"]])
    assert no_answers.exit_code == 1 and "--resume braucht --answers" in no_answers.output
