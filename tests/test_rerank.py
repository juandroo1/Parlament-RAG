"""Reranker (Task 6.1a): Cross-Encoder, Neusortierung der Treffer, Einstellungen und Evals."""

import dataclasses
import datetime as dt
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import SecretStr

from parlrag.config import Settings
from parlrag.evals.results import EvalRun, find_previous, run_stem, write_run
from parlrag.generation import AnswerGenerator
from parlrag.generation.pipeline import AskPipeline
from parlrag.retrieval import CrossEncoderReranker, SearchHit, get_reranker
from parlrag.retrieval.retriever import rerank, rerank_passage


def _hit(number: int, **changes: Any) -> SearchHit:
    base = SearchHit(
        chunk_id=uuid.UUID(int=number),
        document_id=uuid.UUID(int=100 + number),
        chunk_index=0,
        text=f"Abschnitt {number}",
        section=None,
        score=1 / (60 + number),
        rank=number,
        fulltext_rank=None,
        fulltext_score=None,
        vector_rank=number,
        vector_similarity=0.7 - number / 100,
        source_type="transcript",
        source_id=str(number),
        language="de",
        title=f"Titel {number}",
        speaker_name="Rösti Albert",
        parl_group=None,
        canton="BE",
        council="NR",
        date=dt.date(2026, 9, 30),
        debate_dates=(),
        debate_councils=(),
        business_numbers=(),
        url=f"https://www.parlament.ch/{number}",
    )
    return dataclasses.replace(base, **changes)


class FakeReranker:
    model_name = "fake/reranker"

    def __init__(self, scores: dict[str, float]) -> None:
        self.scores = scores
        self.calls: list[tuple[str, list[str]]] = []

    def score(self, query: str, passages: Sequence[str]) -> list[float]:
        self.calls.append((query, list(passages)))
        return [self.scores.get(passage.rsplit("\n", 1)[-1], 0.0) for passage in passages]


def test_rerank_reorders_the_head_and_keeps_the_tail() -> None:
    hits = [_hit(n) for n in range(1, 6)]
    reranker = FakeReranker({"Abschnitt 1": 0.1, "Abschnitt 2": 0.2, "Abschnitt 3": 0.9})
    result = rerank("Frage?", hits, reranker, candidates=3)

    assert [hit.source_id for hit in result] == ["3", "2", "1", "4", "5"]
    assert [hit.rank for hit in result] == [1, 2, 3, 4, 5]
    assert [hit.rerank_score for hit in result] == [0.9, 0.2, 0.1, None, None]
    assert result[0].vector_rank == 3  # ursprüngliche Ränge bleiben zur Analyse erhalten
    ((query, passages),) = reranker.calls
    assert query == "Frage?" and len(passages) == 3  # nur die Kandidaten


def test_rerank_passage_contains_speaker_title_section_and_text() -> None:
    hit = _hit(1, section="Stellungnahme des Bundesrates")
    assert (
        rerank_passage(hit) == "Rösti Albert\nTitel 1\nStellungnahme des Bundesrates\nAbschnitt 1"
    )
    assert rerank_passage(_hit(2, speaker_name=None)) == "Titel 2\nAbschnitt 2"


def test_rerank_with_fewer_hits_than_candidates() -> None:
    result = rerank("Frage?", [_hit(1)], FakeReranker({"Abschnitt 1": 0.5}), candidates=30)
    assert [hit.rerank_score for hit in result] == [0.5]


class FakeModel:
    def __init__(self) -> None:
        self.calls: list[Any] = []

    def predict(self, pairs: list[tuple[str, str]], **kwargs: Any) -> list[float]:
        self.calls.append((pairs, kwargs))
        return [0.25 * (index + 1) for index in range(len(pairs))]


def test_cross_encoder_loads_lazily_once() -> None:
    model = FakeModel()
    loads: list[tuple[str, str, int]] = []

    def loader(name: str, device: str, max_length: int) -> FakeModel:
        loads.append((name, device, max_length))
        return model

    reranker = CrossEncoderReranker("BAAI/bge-reranker-v2-m3", loader=loader)
    assert not reranker.model_loaded and reranker.score("Frage?", []) == []
    assert loads == []  # leere Liste lädt das Modell nicht

    assert reranker.score("Frage?", ["a", "b"]) == [0.25, 0.5]
    assert reranker.score("Frage?", ["c"]) == [0.25]
    assert loads == [("BAAI/bge-reranker-v2-m3", "cpu", 512)]
    pairs, kwargs = model.calls[0]
    assert pairs == [("Frage?", "a"), ("Frage?", "b")]
    assert kwargs["batch_size"] == 16 and kwargs["show_progress_bar"] is False


def _settings(**values: Any) -> Settings:
    return Settings(_env_file=None, postgres_password=SecretStr("x"), **values)


def test_reranker_is_off_by_default() -> None:
    settings = _settings()
    assert settings.retrieval_rerank is False and get_reranker(settings) is None
    assert settings.reranker_model == "BAAI/bge-reranker-v2-m3"
    assert settings.rerank_candidates == 30


def test_reranker_from_settings() -> None:
    reranker = get_reranker(
        _settings(retrieval_rerank=True, reranker_model="x/y", reranker_max_length=256)
    )
    assert isinstance(reranker, CrossEncoderReranker)
    assert reranker.model_name == "x/y" and not reranker.model_loaded
    assert reranker.max_length == 256
    assert _settings().reranker_max_length == 512


def test_pipeline_warm_up_loads_the_reranker() -> None:
    class Retriever:
        embedder = None

        def __init__(self) -> None:
            self.reranker = FakeReranker({})

        def search(self, *args: Any, **kwargs: Any) -> list[SearchHit]:
            return []

    retriever = Retriever()
    pipeline = AskPipeline(retriever, AnswerGenerator(llm=None))  # type: ignore[arg-type]
    assert pipeline.warm_up() is not None
    assert retriever.reranker.calls == [("Modell laden", ["Modell laden"])]


def _run(rerank_on: bool, created: dt.datetime) -> EvalRun:
    return EvalRun(
        created_at=created,
        git_sha="abc1234def",
        git_dirty=False,
        suite="full",
        mode="vector",
        rerank=rerank_on,
        golden="evals/datasets/golden.jsonl",
        questions_total=0,
        skipped_unanswerable=0,
        config={},
        corpus={},
        metrics={},
        subsets={},
        questions=[],
    )


def test_rerank_runs_have_own_files_and_previous(tmp_path: Path) -> None:
    day = dt.datetime(2026, 11, 15, 10, tzinfo=dt.UTC)
    assert run_stem(_run(True, day)) == "2026-11-15_abc1234_full-vector-rerank"
    plain = write_run(_run(False, day), None, tmp_path)
    reranked = write_run(_run(True, day + dt.timedelta(hours=1)), None, tmp_path)

    assert find_previous(tmp_path, "full", "vector") == plain
    assert find_previous(tmp_path, "full", "vector", rerank=True) == reranked
