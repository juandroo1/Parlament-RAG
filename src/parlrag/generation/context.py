"""Nummerierte Quellen für das LLM (plan.md, Abschnitt 7).

Das Modell sieht pro Quelle eine Kopfzeile mit Rat, Datum, Redner bzw. Geschäft und den Text,
nummeriert von [1] bis [k], aber keine Chunk- oder Dokument-IDs.
"""

from collections.abc import Sequence

from parlrag.index.header import (
    BUSINESS_LABEL,
    COUNCIL_NAMES,
    FEDERAL_COUNCIL,
    SEPARATOR,
    SUBMITTED,
)
from parlrag.retrieval import SearchHit
from parlrag.retrieval.fulltext import detect_query_language

MAX_TITLE_CHARS = 200
# Am Ende der Nachricht, weil das Modell sonst bei Quellen in der anderen Sprache leicht
# in deren Sprache antwortet (beobachtet in Task 4.2).
LANGUAGE_INSTRUCTIONS = {
    "de": "Antworte auf Deutsch, auch wenn Quellen auf Französisch sind.",
    "fr": "Antworte auf Französisch, auch wenn Quellen auf Deutsch sind.",
}


def _shorten(text: str, limit: int = MAX_TITLE_CHARS) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"


def _speaker(hit: SearchHit) -> str | None:
    if not hit.speaker_name:
        return None
    if hit.speaker_function and hit.speaker_function.startswith("BR"):
        return f"{hit.speaker_name} ({FEDERAL_COUNCIL.get(hit.language, 'Bundesrat')})"
    details = ", ".join(part for part in (hit.parl_group, hit.canton) if part)
    return f"{hit.speaker_name} ({details})" if details else hit.speaker_name


def source_header(hit: SearchHit) -> str:
    """Z. B. `Ständerat · 15.09.2026 · Michel Matthias (RL, ZG) · 25.3866 Motion …`."""
    language = hit.language if hit.language in COUNCIL_NAMES else "de"
    if hit.source_type == "business":
        number = ", ".join(hit.business_numbers)
        parts = [
            f"{BUSINESS_LABEL[language]} {number}".strip(),
            hit.section,
            _shorten(hit.title),
            f"{SUBMITTED[language]} {hit.date:%d.%m.%Y}",
        ]
    else:
        parts = [
            COUNCIL_NAMES[language].get(hit.council or "", hit.council),
            f"{hit.date:%d.%m.%Y}",
            _speaker(hit),
            _shorten(hit.title),
        ]
    return SEPARATOR.join(part for part in parts if part)


def format_sources(hits: Sequence[SearchHit]) -> str:
    blocks = [
        f"[{number}] {source_header(hit)}\n{hit.text.strip()}"
        for number, hit in enumerate(hits, start=1)
    ]
    return "\n\n".join(blocks)


def build_user_message(
    question: str, hits: Sequence[SearchHit], feedback: str | None = None
) -> str:
    """Quellen, Frage, Anweisung zur Antwortsprache und beim Retry der konkrete Fehler."""
    parts = ["Quellen:", format_sources(hits), f"Frage: {question.strip()}"]
    language = detect_query_language(question)
    if language:
        parts.append(LANGUAGE_INSTRUCTIONS[language])
    if feedback:
        parts.append(
            f"Deine vorherige Antwort war ungültig: {feedback} "
            "Antworte erneut und halte die Regeln ein."
        )
    return "\n\n".join(parts)
