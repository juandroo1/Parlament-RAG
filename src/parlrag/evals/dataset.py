"""Goldset `evals/datasets/golden.jsonl`: Schema und Laden (Task 3.1, plan.md Abschnitt 9).

Eine Zeile pro Frage. Erwartete Quellen sind Dokumente im Format `<source_type>:<source_id>`
(ein Votum oder ein Geschäftstext), nie Chunks. Fragen und Quellen bestimmt ein Mensch.
"""

import json
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from parlrag.ingest.mapping import Language
from parlrag.retrieval.filters import SearchFilters

DEFAULT_GOLDEN_PATH = Path("evals/datasets/golden.jsonl")

# fr: Frage auf Französisch; crosslingual: erwartete Voten in der anderen Sprache;
# filter: Frage mit Filter; unanswerable: Korpus enthält keine Antwort; wertend: verlangt eine
# Bewertung (AK-7.1); teilkorpus: Quellen in der Herbstsession 2026; smoke: Smoke-Suite.
Tag = Literal["fr", "crosslingual", "filter", "unanswerable", "wertend", "teilkorpus", "smoke"]

SourceId = Annotated[str, Field(pattern=r"^(transcript|business):[0-9]+$")]


class GoldenSetError(ValueError):
    """Das Goldset ist ungültig (mit Zeilennummer)."""


class GoldenItem(BaseModel):
    """Eine Frage des Goldsets mit den erwarteten Quellen."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^q[0-9]{2,3}$")
    question: str = Field(min_length=10)
    language: Language
    filters: SearchFilters | None = None
    expected_source_ids: tuple[SourceId, ...]
    answerable: bool
    tags: tuple[Tag, ...] = ()
    notes: str | None = None

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        problems = []
        if len(set(self.tags)) != len(self.tags):
            problems.append("Tag doppelt")
        if len(set(self.expected_source_ids)) != len(self.expected_source_ids):
            problems.append("Quelle doppelt")
        if self.answerable == self.has("unanswerable"):
            problems.append("`answerable` passt nicht zum Tag `unanswerable`")
        if self.answerable != bool(self.expected_source_ids):
            problems.append("beantwortbare Fragen brauchen Quellen, unbeantwortbare keine")
        if self.has("wertend") and not self.answerable:
            problems.append("wertende Fragen sind beantwortbar (Entscheidungsprotokoll 3.1)")
        if self.has("fr") != (self.language == "fr"):
            problems.append("Tag `fr` passt nicht zur Sprache")
        if self.has("filter") != (self.filters is not None):
            problems.append("Tag `filter` passt nicht zu `filters`")
        if self.filters is not None and self.filters == SearchFilters():
            problems.append("`filters` ist leer")
        if problems:
            raise ValueError("; ".join(problems))
        return self

    def has(self, tag: Tag) -> bool:
        return tag in self.tags


def load_golden(path: Path = DEFAULT_GOLDEN_PATH) -> list[GoldenItem]:
    """Liest das Goldset; leere Zeilen werden übersprungen, IDs müssen eindeutig sein."""
    items: list[GoldenItem] = []
    seen: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = GoldenItem.model_validate(json.loads(line))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise GoldenSetError(f"{path.name}, Zeile {number}: {exc}") from exc
        if item.id in seen:
            raise GoldenSetError(f"{path.name}, Zeile {number}: ID {item.id} doppelt")
        seen.add(item.id)
        items.append(item)
    return items
