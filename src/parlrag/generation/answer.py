"""Antwort mit Quellennummern und Zitatvalidierung (Task 4.2; plan.md, Abschnitt 7; AK-2.3).

Das Modell liefert nur Nummern [n] der übergebenen Quellen; der Server ordnet sie den Chunks zu.
Massgebend sind die Nummern im Antworttext:

- Jede Nummer liegt zwischen 1 und k (sonst erfunden).
- Jede Nummer im Text steht auch in `citations`.
- Ohne `insufficient_context` enthält die Antwort mindestens eine Nummer (AK-1.2).

Bei einem Verstoss folgt ein Retry mit dem konkreten Fehler, danach `CitationError`. Nummern in
`citations`, die im Text fehlen, werden gestrichen: Sie sind unsichtbar und keinen Retry wert.

«Keine ausreichende Grundlage» (Task 4.3, AK-3.1): keine Treffer, beste Cosine-Similarity unter
der Schwelle (dann ohne LLM-Aufruf) oder `insufficient_context` vom Modell. In allen Fällen steht
ein fester Hinweis in der Sprache der Frage, ohne Quellen.
"""

import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

from parlrag.generation.context import build_user_message
from parlrag.llm import LLMClient, LLMOutputError, Usage, sum_usage
from parlrag.prompts import Prompt, load_prompt
from parlrag.retrieval import SearchHit, best_similarity
from parlrag.retrieval.fulltext import detect_query_language

logger = logging.getLogger(__name__)

DEFAULT_CONTEXT_CHUNKS = 8
DEFAULT_MIN_SIMILARITY = 0.55
MAX_ATTEMPTS = 2
INSUFFICIENT_NOTICE = {
    "de": "Zu dieser Frage habe ich in den Debatten und Geschäften des Bundesparlaments keine "
    "ausreichende Grundlage gefunden.",
    "fr": "Je n'ai pas trouvé de base suffisante pour répondre à cette question dans les débats "
    "et les objets du Parlement fédéral.",
}

# no_hits: keine Treffer; low_similarity: Schwelle; model: `insufficient_context` vom Modell.
InsufficientReason = Literal["no_hits", "low_similarity", "model"]

# [3], [1, 2] und [1][2] (Letzteres als zwei Treffer).
CITATION_PATTERN = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


class AnswerOutput(BaseModel):
    """Strukturierte Ausgabe des Modells (plan.md, Abschnitt 7)."""

    answer: str = Field(description="Antwort mit Quellennummern [n] im Text.")
    citations: list[int] = Field(description="Alle Quellennummern, die im Text vorkommen.")
    insufficient_context: bool = Field(
        description="true, wenn die Quellen die Frage nicht beantworten."
    )


@dataclass(frozen=True)
class CitedSource:
    """Eine zitierte Quelle: Nummer im Antworttext und der übergebene Chunk mit Metadaten."""

    number: int
    hit: SearchHit


@dataclass(frozen=True)
class GeneratedAnswer:
    answer: str
    insufficient_context: bool
    sources: list[CitedSource]
    context: list[SearchHit]  # alle übergebenen Chunks, Nummer = Position + 1
    usage: Usage | None
    attempts: int
    prompt_version: str
    dropped_citations: list[int] = field(default_factory=list)
    insufficient_reason: InsufficientReason | None = None
    best_similarity: float | None = None
    model_answer: str | None = None  # Text des Modells, auch wenn der feste Hinweis gilt


class CitationError(LLMOutputError):
    """Die Antwort verletzt auch nach dem Retry die Zitatregeln."""


def citations_in_text(text: str) -> list[int]:
    """Quellennummern in der Reihenfolge ihres ersten Vorkommens."""
    numbers: list[int] = []
    for match in CITATION_PATTERN.finditer(text):
        for part in match.group(1).split(","):
            number = int(part)
            if number not in numbers:
                numbers.append(number)
    return numbers


def citation_problems(output: AnswerOutput, k: int) -> list[str]:
    """Verstösse gegen die Zitatregeln; leer, wenn die Antwort gültig ist."""
    cited = citations_in_text(output.answer)
    problems = []
    invented = [n for n in cited if not 1 <= n <= k]
    if invented:
        listed = ", ".join(f"[{n}]" for n in invented)
        problems.append(f"Die Quellen {listed} gibt es nicht; erlaubt sind [1] bis [{k}].")
    missing = [n for n in cited if n not in output.citations]
    if missing:
        listed = ", ".join(f"[{n}]" for n in missing)
        problems.append(f"Die Nummern {listed} stehen im Text, aber nicht in `citations`.")
    if not cited and not output.insufficient_context:
        problems.append(
            "Die Antwort enthält keine Quellennummer. Belege jede Aussage mit [n] oder setze "
            "`insufficient_context` auf true."
        )
    return problems


class AnswerGenerator:
    def __init__(
        self,
        llm: LLMClient,
        *,
        context_chunks: int = DEFAULT_CONTEXT_CHUNKS,
        min_similarity: float = DEFAULT_MIN_SIMILARITY,
        prompt: Prompt | None = None,
        max_attempts: int = MAX_ATTEMPTS,
    ) -> None:
        self.llm = llm
        self.context_chunks = context_chunks
        self.min_similarity = min_similarity
        self.prompt = prompt or load_prompt("answer")
        self.max_attempts = max_attempts

    def generate(self, question: str, hits: Sequence[SearchHit]) -> GeneratedAnswer:
        context = list(hits[: self.context_chunks])
        if not context:
            return self._insufficient(question, "no_hits", context=[], best=None)
        best = best_similarity(hits)
        if best is None:
            logger.info("Keine Vektor-Similarity (Suchart ohne Vektor); Schwelle entfällt")
        elif best < self.min_similarity:
            logger.info(
                "Beste Similarity %.3f unter %.3f: kein LLM-Aufruf", best, self.min_similarity
            )
            return self._insufficient(question, "low_similarity", context=context, best=best)

        usages: list[Usage] = []
        feedback: str | None = None
        for attempt in range(1, self.max_attempts + 1):
            result = self.llm.generate(
                system=self.prompt.text,
                user=build_user_message(question, context, feedback),
                schema=AnswerOutput,
            )
            usages.append(result.usage)
            problems = citation_problems(result.output, len(context))
            if not problems and result.output.insufficient_context:
                return self._insufficient(
                    question,
                    "model",
                    context=context,
                    best=best,
                    usages=usages,
                    attempts=attempt,
                    model_answer=result.output.answer.strip(),
                )
            if not problems:
                return self._answer(result.output, context, usages, attempt, best)
            feedback = " ".join(problems)
            logger.warning("Zitatregeln verletzt (Versuch %d): %s", attempt, feedback)
        raise CitationError(
            f"Antwort verletzt die Zitatregeln nach {self.max_attempts} Versuchen: {feedback}",
            sum_usage(usages),
        )

    def _insufficient(
        self,
        question: str,
        reason: InsufficientReason,
        *,
        context: list[SearchHit],
        best: float | None,
        usages: Sequence[Usage] = (),
        attempts: int = 0,
        model_answer: str | None = None,
    ) -> GeneratedAnswer:
        """Fester Hinweis in der Sprache der Frage, ohne Quellen (AK-3.1)."""
        language = detect_query_language(question) or "de"
        return GeneratedAnswer(
            answer=INSUFFICIENT_NOTICE[language],
            insufficient_context=True,
            sources=[],
            context=context,
            usage=sum_usage(usages),
            attempts=attempts,
            prompt_version=self.prompt.version,
            insufficient_reason=reason,
            best_similarity=best,
            model_answer=model_answer,
        )

    def _answer(
        self,
        output: AnswerOutput,
        context: list[SearchHit],
        usages: list[Usage],
        attempts: int,
        best: float | None,
    ) -> GeneratedAnswer:
        cited = citations_in_text(output.answer)
        dropped = [n for n in output.citations if n not in cited]
        if dropped:
            logger.info("Nicht im Text zitierte Nummern gestrichen: %s", dropped)
        return GeneratedAnswer(
            answer=output.answer.strip(),
            insufficient_context=output.insufficient_context,
            sources=[CitedSource(number=n, hit=context[n - 1]) for n in cited],
            context=context,
            usage=sum_usage(usages),
            attempts=attempts,
            prompt_version=self.prompt.version,
            dropped_citations=dropped,
            best_similarity=best,
            model_answer=output.answer.strip(),
        )
