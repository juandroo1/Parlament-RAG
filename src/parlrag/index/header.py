"""Kontext-Header für das Embedding (plan.md, Abschnitt 5; Entscheidungsprotokoll, Task 2.1).

Beispiel: `Ständerat · 15.09.2026 · Michel Matthias (RL, ZG) · 25.3866 Einführung …`.
Gespeichert wird der Chunk ohne Header, eingebettet mit Header.
"""

from parlrag.index.chunker import TITLE_SECTION, ChunkData
from parlrag.ingest.mapping import DocumentData

SEPARATOR = " · "
MAX_TITLE_CHARS = 300

COUNCIL_NAMES = {
    "de": {"NR": "Nationalrat", "SR": "Ständerat", "V": "Vereinigte Bundesversammlung"},
    "fr": {
        "NR": "Conseil national",
        "SR": "Conseil des Etats",
        "V": "Assemblée fédérale (Chambres réunies)",
    },
}
FEDERAL_COUNCIL = {"de": "Bundesrat", "fr": "Conseil fédéral"}
BUSINESS_LABEL = {"de": "Geschäft", "fr": "Objet"}
SUBMITTED = {"de": "eingereicht", "fr": "déposé le"}


def _shorten(text: str, limit: int = MAX_TITLE_CHARS) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0] + "…"


def _speaker(document: DocumentData) -> str | None:
    if not document.speaker_name:
        return None
    if document.parl_group:
        details = ", ".join(part for part in (document.parl_group, document.canton) if part)
        return f"{document.speaker_name} ({details})"
    if document.speaker_function and document.speaker_function.startswith("BR"):
        return f"{document.speaker_name} ({FEDERAL_COUNCIL[document.language]})"
    return document.speaker_name


def context_header(document: DocumentData, chunk: ChunkData) -> str:
    language = document.language
    date = document.date.strftime("%d.%m.%Y")
    parts: list[str | None]
    if document.source_type == "transcript":
        council = COUNCIL_NAMES[language].get(document.council) if document.council else None
        parts = [council, date, _speaker(document), _shorten(document.title)]
    else:
        number = document.business_numbers[0] if document.business_numbers else None
        section = chunk.metadata.get("section")
        parts = [
            f"{BUSINESS_LABEL[language]} {number}" if number else BUSINESS_LABEL[language],
            f"{SUBMITTED[language]} {date}",
            _shorten(document.title),
            section if section and section != TITLE_SECTION[language] else None,
        ]
    return SEPARATOR.join(part for part in parts if part)


def embedding_text(document: DocumentData, chunk: ChunkData, *, with_header: bool = True) -> str:
    """Text, der eingebettet wird: Header und Chunk (Experiment «ohne Header»: nur der Chunk)."""
    if not with_header:
        return chunk.text
    return f"{context_header(document, chunk)}\n\n{chunk.text}"
