"""LLM-as-Judge für die Antwort-Evals (Task 4.5a; plan.md, Abschnitt 9).

Der Judge sieht die Frage, die nummerierten Quellen genau so, wie das Antwortmodell sie sah,
und die Antwort. Er zerlegt die Antwort in Aussagen und beurteilt pro Aussage jede zitierte
Quelle sowie die Stützung insgesamt; dazu, ob die Antwort selbst wertet (AK-7.1).
"""

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, Field

from parlrag.generation.context import format_sources
from parlrag.llm import LLMClient, Usage
from parlrag.prompts import Prompt, load_prompt
from parlrag.retrieval import SearchHit

Support = Literal["supported", "partial", "unsupported"]
SUPPORT_SCORE: dict[str, float] = {"supported": 1.0, "partial": 0.5, "unsupported": 0.0}


class CitationVerdict(BaseModel):
    number: int = Field(description="Zitierte Quellennummer.")
    supports: bool = Field(description="Stützt genau diese Quelle die Aussage?")


class StatementVerdict(BaseModel):
    statement: str = Field(description="Die Aussage, wörtlich oder knapp gekürzt.")
    citations: list[CitationVerdict] = Field(description="Zitierte Quellen der Aussage.")
    support: Support = Field(description="Stützung durch alle Quellen zusammen.")


class JudgeOutput(BaseModel):
    statements: list[StatementVerdict]
    contains_own_evaluation: bool = Field(
        description="true, wenn die Antwort selbst bewertet oder eine Empfehlung abgibt."
    )
    evaluation_note: str = Field(description="Kurzes Zitat als Begründung, sonst leer.")


def citation_accuracy(output: JudgeOutput) -> float | None:
    """Anteil der Paare (Aussage, zitierte Quelle), bei denen die Quelle die Aussage stützt."""
    pairs = [citation.supports for item in output.statements for citation in item.citations]
    return sum(pairs) / len(pairs) if pairs else None


def faithfulness(output: JudgeOutput) -> float | None:
    """Mittlere Stützung der Aussagen (gestützt 1, teilweise 0.5, nicht gestützt 0)."""
    scores = [SUPPORT_SCORE[item.support] for item in output.statements]
    return sum(scores) / len(scores) if scores else None


def build_judge_message(question: str, context: Sequence[SearchHit], answer: str) -> str:
    return "\n\n".join(
        ["Frage:", question.strip(), "Quellen:", format_sources(context), "Antwort:", answer]
    )


class Judge:
    def __init__(self, llm: LLMClient, prompt: Prompt | None = None) -> None:
        self.llm = llm
        self.prompt = prompt or load_prompt("judge")

    @property
    def model(self) -> str:
        return self.llm.model

    def judge(
        self, question: str, context: Sequence[SearchHit], answer: str
    ) -> tuple[JudgeOutput, Usage]:
        result = self.llm.generate(
            system=self.prompt.text,
            user=build_judge_message(question, context, answer),
            schema=JudgeOutput,
        )
        return result.output, result.usage
