"""Antwort mit Quellennummern und Zitatvalidierung (Task 4.2, AK-2.3), mit Fake-LLM."""

import dataclasses
import datetime as dt
import uuid
from typing import Any

import pytest
from pydantic import BaseModel

from parlrag.generation import (
    INSUFFICIENT_NOTICE,
    AnswerGenerator,
    AnswerOutput,
    CitationError,
    citation_problems,
    citations_in_text,
)
from parlrag.generation.context import build_user_message, source_header
from parlrag.llm import LLMResult, Usage
from parlrag.prompts import load_prompt
from parlrag.retrieval import SearchHit

SPEECH = SearchHit(
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
BUSINESS = dataclasses.replace(
    SPEECH,
    chunk_id=uuid.UUID(int=3),
    document_id=uuid.UUID(int=4),
    text="Le Conseil fédéral propose de rejeter la motion.",
    section="Avis du Conseil fédéral",
    source_type="business",
    source_id="20253906",
    language="fr",
    title="Valeurs limites de PFAS",
    speaker_name=None,
    speaker_function=None,
    canton=None,
    council=None,
    date=dt.date(2025, 6, 20),
    business_numbers=("25.3906",),
)
GROUP_SPEECH = dataclasses.replace(
    SPEECH,
    chunk_id=uuid.UUID(int=5),
    speaker_name="Michel Matthias",
    speaker_function=None,
    parl_group="RL",
    canton="ZG",
    council="SR",
)
HITS = [SPEECH, BUSINESS, GROUP_SPEECH]


def _usage(cost: float | None = 0.01) -> Usage:
    return Usage(model="claude-haiku-5-5", input_tokens=1000, output_tokens=100, cost_usd=cost)


class FakeLLM:
    model = "claude-haiku-5-5"

    def __init__(self, *outputs: AnswerOutput, cost: float | None = 0.01) -> None:
        self.outputs = list(outputs)
        self.cost = cost
        self.calls: list[dict[str, Any]] = []

    def generate[T: BaseModel](self, *, system: str, user: str, schema: type[T]) -> LLMResult[T]:
        self.calls.append({"system": system, "user": user, "schema": schema})
        output = self.outputs.pop(0)
        assert isinstance(output, schema)
        return LLMResult(output=output, usage=_usage(self.cost))


def _out(answer: str, citations: list[int], insufficient: bool = False) -> AnswerOutput:
    return AnswerOutput(answer=answer, citations=citations, insufficient_context=insufficient)


def test_citations_in_text() -> None:
    text = "Erstens [2]. Zweitens [1, 3]. Drittens [3][4]. Kein Zitat: [a], [ 5 ]. Wieder [2]."
    assert citations_in_text(text) == [2, 1, 3, 4]


@pytest.mark.parametrize(
    ("output", "problem"),
    [
        (_out("Aussage [4].", [4]), "Die Quellen [4] gibt es nicht; erlaubt sind [1] bis [3]."),
        (_out("Aussage [0].", [0]), "Die Quellen [0] gibt es nicht"),
        (_out("Aussage [1][2].", [1]), "Die Nummern [2] stehen im Text, aber nicht in `citations`"),
        (_out("Aussage ohne Beleg.", []), "keine Quellennummer"),
    ],
)
def test_citation_problems(output: AnswerOutput, problem: str) -> None:
    problems = citation_problems(output, k=3)
    assert len(problems) == 1 and problem in problems[0]


def test_valid_outputs_have_no_problems() -> None:
    assert citation_problems(_out("Aussage [1]. Weitere [3].", [1, 3]), k=3) == []
    assert citation_problems(_out("Die Quellen beantworten die Frage nicht.", [], True), k=3) == []
    assert citation_problems(_out("Text [1].", [1, 2]), k=3) == []  # überzählige: kein Fehler


def test_numbers_are_mapped_to_the_given_chunks() -> None:
    llm = FakeLLM(_out("Rösti betont den Winter [1]. Der Bundesrat lehnt ab [2].", [1, 2]))
    result = AnswerGenerator(llm).generate("Was sagte Rösti zum Winterstrom?", HITS)

    assert [(s.number, s.hit) for s in result.sources] == [(1, SPEECH), (2, BUSINESS)]
    assert result.context == HITS
    assert result.answer.startswith("Rösti betont")
    assert not result.insufficient_context
    assert result.attempts == 1
    assert result.usage is not None and result.usage.cost_usd == pytest.approx(0.01)
    assert result.prompt_version == load_prompt("answer").version
    assert llm.calls[0]["schema"] is AnswerOutput
    assert llm.calls[0]["system"] == load_prompt("answer").text


def test_sources_follow_order_of_first_citation() -> None:
    llm = FakeLLM(_out("Zuerst [3], dann [1], nochmals [3].", [1, 3]))
    result = AnswerGenerator(llm).generate("Frage?", HITS)
    assert [s.number for s in result.sources] == [3, 1]


def test_extra_citations_are_dropped() -> None:
    llm = FakeLLM(_out("Nur eine Aussage [1].", [1, 2]))
    result = AnswerGenerator(llm).generate("Frage?", HITS)

    assert [s.number for s in result.sources] == [1]
    assert result.dropped_citations == [2]
    assert result.attempts == 1


def test_invented_number_triggers_retry_with_feedback() -> None:
    llm = FakeLLM(_out("Erfunden [7].", [7]), _out("Korrigiert [2].", [2]))
    result = AnswerGenerator(llm).generate("Frage?", HITS)

    assert result.attempts == 2
    assert [s.hit for s in result.sources] == [BUSINESS]
    assert "Die Quellen [7] gibt es nicht" in llm.calls[1]["user"]
    assert "Deine vorherige Antwort war ungültig" not in llm.calls[0]["user"]
    assert result.usage is not None
    assert result.usage.cost_usd == pytest.approx(0.02)  # beide Versuche
    assert result.usage.input_tokens == 2000


def test_missing_citation_in_list_triggers_retry() -> None:
    llm = FakeLLM(_out("A [1]. B [2].", [1]), _out("A [1]. B [2].", [1, 2]))
    assert AnswerGenerator(llm).generate("Frage?", HITS).attempts == 2


def test_persistent_violation_raises_with_cost_of_all_attempts() -> None:
    llm = FakeLLM(_out("Erfunden [9].", [9]), _out("Wieder erfunden [8].", [8]))
    with pytest.raises(CitationError, match=r"\[8\] gibt es nicht") as info:
        AnswerGenerator(llm).generate("Frage?", HITS)

    assert len(llm.calls) == 2
    assert info.value.usage is not None and info.value.usage.cost_usd == pytest.approx(0.02)


def test_unknown_cost_stays_unknown_over_attempts() -> None:
    llm = FakeLLM(_out("Erfunden [9].", [9]), _out("Gut [1].", [1]), cost=None)
    result = AnswerGenerator(llm).generate("Frage?", HITS)
    assert result.usage is not None and result.usage.cost_usd is None


def test_model_signal_gives_fixed_notice_and_keeps_model_text() -> None:
    llm = FakeLLM(_out("Die gefundenen Quellen beantworten die Frage nicht.", [], True))
    result = AnswerGenerator(llm).generate("Was beschloss der Bieler Stadtrat?", HITS)

    assert result.insufficient_context and result.insufficient_reason == "model"
    assert result.answer == INSUFFICIENT_NOTICE["de"]
    assert result.model_answer == "Die gefundenen Quellen beantworten die Frage nicht."
    assert result.sources == [] and result.attempts == 1
    assert result.usage is not None  # Kosten des Aufrufs bleiben sichtbar
    assert result.best_similarity == pytest.approx(0.70)


def test_model_signal_with_citations_shows_no_sources() -> None:
    llm = FakeLLM(_out("Die Quellen behandeln anderes [1].", [1], True))
    result = AnswerGenerator(llm).generate("Frage?", HITS)
    assert result.insufficient_reason == "model" and result.sources == []


def _with_similarity(similarity: float | None) -> list[SearchHit]:
    return [dataclasses.replace(hit, vector_similarity=similarity) for hit in HITS]


def test_low_similarity_skips_the_llm() -> None:
    llm = FakeLLM()
    hits = _with_similarity(0.50)
    result = AnswerGenerator(llm, min_similarity=0.55).generate("Wer gewann den Final?", hits)

    assert llm.calls == []
    assert result.insufficient_context and result.insufficient_reason == "low_similarity"
    assert result.answer == INSUFFICIENT_NOTICE["de"]
    assert result.best_similarity == pytest.approx(0.50)
    assert result.usage is None and result.attempts == 0 and result.sources == []


def test_similarity_at_threshold_goes_to_the_llm() -> None:
    llm = FakeLLM(_out("Aussage [1].", [1]))
    result = AnswerGenerator(llm, min_similarity=0.55).generate("Frage?", _with_similarity(0.55))
    assert len(llm.calls) == 1 and not result.insufficient_context
    assert result.insufficient_reason is None


def test_best_similarity_over_all_hits_counts() -> None:
    hits = [dataclasses.replace(SPEECH, vector_similarity=None), *_with_similarity(0.61)[1:]]
    llm = FakeLLM(_out("Aussage [2].", [2]))
    result = AnswerGenerator(llm, min_similarity=0.60).generate("Frage?", hits)
    assert result.best_similarity == pytest.approx(0.61) and len(llm.calls) == 1


def test_search_without_similarity_skips_the_threshold() -> None:
    llm = FakeLLM(_out("Aussage [1].", [1]))
    result = AnswerGenerator(llm, min_similarity=0.99).generate("Frage?", _with_similarity(None))
    assert len(llm.calls) == 1 and result.best_similarity is None


def test_notice_in_french() -> None:
    llm = FakeLLM()
    result = AnswerGenerator(llm, min_similarity=0.9).generate(
        "Qu'a décidé le conseil municipal de Bienne ?", HITS
    )
    assert result.answer == INSUFFICIENT_NOTICE["fr"]


def test_no_hits_means_no_llm_call() -> None:
    llm = FakeLLM()
    result = AnswerGenerator(llm).generate("Frage?", [])

    assert result.insufficient_context and result.usage is None and result.attempts == 0
    assert result.insufficient_reason == "no_hits" and result.answer == INSUFFICIENT_NOTICE["de"]
    assert llm.calls == []


def test_only_top_k_chunks_are_given() -> None:
    llm = FakeLLM(_out("Aussage [2].", [2]))
    result = AnswerGenerator(llm, context_chunks=2).generate("Frage?", HITS)

    assert result.context == HITS[:2]
    assert "[3]" not in llm.calls[0]["user"]


def test_invalid_numbers_are_judged_against_k() -> None:
    llm = FakeLLM(_out("Aussage [3].", [3]), _out("Aussage [1].", [1]))
    result = AnswerGenerator(llm, context_chunks=2).generate("Frage?", HITS)
    assert result.attempts == 2  # [3] wäre bei k = 2 erfunden


def test_source_headers() -> None:
    assert source_header(SPEECH) == (
        "Nationalrat · 30.09.2026 · Rösti Albert (Bundesrat) · "
        "26.9022 Aktuelle Debatte. Hitzewelle und Dürre"
    )
    assert source_header(GROUP_SPEECH).startswith(
        "Ständerat · 30.09.2026 · Michel Matthias (RL, ZG)"
    )
    assert source_header(BUSINESS) == (
        "Objet 25.3906 · Avis du Conseil fédéral · Valeurs limites de PFAS · déposé le 20.06.2025"
    )


def test_user_message_numbers_sources_without_ids() -> None:
    message = build_user_message("Pourquoi le Conseil fédéral parle-t-il de l'hiver ?", HITS)

    assert message.startswith(  # Anweisung zur Sprache am Anfang und am Ende
        "Antworte auf Französisch, auch wenn Quellen auf Deutsch sind.\n\nQuellen:\n\n"
        "[1] Nationalrat · 30.09.2026"
    )
    assert "\n\n[2] Objet 25.3906" in message and "\n\n[3] Ständerat" in message
    assert "Wir brauchen den Strom vor allem im Winter." in message
    assert message.rstrip().endswith(
        "Frage: Pourquoi le Conseil fédéral parle-t-il de l'hiver ?\n\n"
        "Antworte auf Französisch, auch wenn Quellen auf Deutsch sind."
    )
    for hit in HITS:  # keine IDs (AK-2.3: das Modell kennt nur Nummern)
        assert str(hit.chunk_id) not in message and str(hit.document_id) not in message
        assert hit.source_id not in message


def test_user_message_without_detectable_language() -> None:
    assert "Antworte auf" not in build_user_message("PFAS?", HITS)
    german = build_user_message("Was sagte der Bundesrat zum Winterstrom?", HITS)
    assert german.rstrip().endswith("Antworte auf Deutsch, auch wenn Quellen auf Französisch sind.")
    assert german.startswith("Antworte auf Deutsch")


def test_answer_prompt_contains_core_rules() -> None:
    prompt = load_prompt("answer")
    for rule in (
        "ausschliesslich die nummerierten Quellen",
        "eckigen Klammern",
        "Zitiere nur Quellen, die die Aussage tatsächlich stützen",
        "Sprache der Frage",
        "Bewerte keine Personen, Parteien oder Vorlagen",
        "insufficient_context",
    ):
        assert rule in prompt.text, rule
    assert len(prompt.version) == 12
