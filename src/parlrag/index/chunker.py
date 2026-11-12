"""Chunker gemäss plan.md, Abschnitt 5 (Entscheidungsprotokoll, Task 2.1).

- Voten: kurze bleiben ganz; lange werden in Sätze zerlegt und wieder zusammengesetzt.
  Geschnitten wird bevorzugt an Absatzgrenzen, sobald die (ausgeglichene) Zielgrösse
  erreicht ist, sonst an Satzgrenzen; nie über der Höchstgrösse.
- Overlap: Der nächste Chunk beginnt mit den letzten ganzen Sätzen des vorherigen.
- Geschäfte: ein Titel-Chunk und Chunks pro Abschnitt (`## Überschrift`).

Der Tokenzähler wird übergeben; bis Task 2.2 gilt `approximate_token_count`.
"""

import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from parlrag.config import Settings
from parlrag.ingest.mapping import SECTION_PREFIX, DocumentData

TokenCounter = Callable[[str], int]

PARAGRAPH = "\n\n"
LINE = "\n"
SPACE = " "
MAX_FACTOR = 1.2  # Höchstgrösse = 1,2-mal Zielgrösse
EARLY_PARAGRAPH_CUT = 0.8  # an einer Absatzgrenze schon ab 80 % des Ziels schneiden, wenn nötig
TITLE_SECTION = {"de": "Titel", "fr": "Titre"}

# Kandidat für ein Satzende: . ! ? … (optional mit schliessendem Anführungszeichen oder
# Klammer), Leerraum, dann ein Grossbuchstabe oder öffnendes Zeichen.
_SENTENCE_BREAK = re.compile(
    r"([.!?…])([\"»\N{RIGHT DOUBLE QUOTATION MARK}\N{RIGHT SINGLE QUOTATION MARK})\]]?)"
    r"(\s+)(?=[«„\"(\[A-ZÄÖÜÀÂÉÈÊÎÔÛÇ])"
)
# Nach diesen Wörtern ist ein Punkt kein Satzende (DE/FR, ohne Gross-/Kleinschreibung).
_ABBREVIATIONS = frozenset(
    {
        "abs", "al", "art", "bspw", "bst", "bzw", "ca", "cf", "ch", "dr", "env", "etc", "evtl",
        "ex", "fr", "hr", "inkl", "lit", "mio", "mme", "mmes", "mrd", "nr", "no", "prof", "resp",
        "sog", "st", "usw", "vgl", "ziff",
    }
)  # fmt: skip
_LAST_WORD = re.compile(r"(\w+)$")
_SECTION_HEADING = re.compile(rf"(?:^|{PARAGRAPH}){re.escape(SECTION_PREFIX)}([^\n]+){PARAGRAPH}")


def approximate_token_count(text: str) -> int:
    """Faustregel Zeichen / 4; genaue Zahlen liefert ab Task 2.2 der bge-m3-Tokenizer."""
    return math.ceil(len(text) / 4)


@dataclass(frozen=True)
class ChunkingConfig:
    target_tokens: int = 500
    overlap_ratio: float = 0.15

    @property
    def max_tokens(self) -> int:
        return round(self.target_tokens * MAX_FACTOR)

    @property
    def overlap_tokens(self) -> int:
        return int(self.target_tokens * self.overlap_ratio)

    @classmethod
    def from_settings(cls, settings: Settings) -> "ChunkingConfig":
        return cls(
            target_tokens=settings.chunk_target_tokens,
            overlap_ratio=settings.chunk_overlap_ratio,
        )


@dataclass(frozen=True)
class ChunkData:
    """Ein Chunk ohne Kontext-Header (so wird er gespeichert, plan.md Abschnitt 5)."""

    chunk_index: int
    text: str
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class _Unit:
    text: str
    tokens: int
    separator: str  # Trennzeichen vor dieser Einheit: Absatz, Zeile oder Leerzeichen


def _render(units: list[_Unit]) -> str:
    return "".join(
        (unit.separator if index else "") + unit.text for index, unit in enumerate(units)
    )


def split_sentences(line: str) -> list[str]:
    """Teilt eine Zeile in Sätze; nicht nach Einzelbuchstaben (z. B., M.), Zahlen (5. Oktober)
    und bekannten Abkürzungen (Mio., Art., ca.)."""
    sentences: list[str] = []
    start = 0
    for match in _SENTENCE_BREAK.finditer(line):
        if match.group(1) == ".":
            word = _LAST_WORD.search(line[start : match.start()])
            if word and (
                len(word.group(1)) == 1
                or word.group(1).isdigit()
                or word.group(1).lower() in _ABBREVIATIONS
            ):
                continue
        sentences.append(line[start : match.end(2)])
        start = match.end(3)
    sentences.append(line[start:])
    return [sentence for sentence in sentences if sentence]


def _split_long(text: str, separator: str, max_tokens: int, count: TokenCounter) -> list[_Unit]:
    """Notfall: Satz über der Höchstgrösse an Wortgrenzen teilen."""
    pieces: list[_Unit] = []
    words: list[str] = []
    for word in text.split(SPACE):
        candidate = SPACE.join([*words, word])
        if words and count(candidate) > max_tokens:
            piece = SPACE.join(words)
            pieces.append(_Unit(piece, count(piece), separator if not pieces else SPACE))
            words = [word]
        else:
            words.append(word)
    piece = SPACE.join(words)
    pieces.append(_Unit(piece, count(piece), separator if not pieces else SPACE))
    return pieces


def _units(text: str, max_tokens: int, count: TokenCounter) -> list[_Unit]:
    units: list[_Unit] = []
    for p_index, paragraph in enumerate(text.split(PARAGRAPH)):
        for l_index, line in enumerate(paragraph.split(LINE)):
            for s_index, sentence in enumerate(split_sentences(line)):
                if s_index:
                    separator = SPACE
                elif l_index:
                    separator = LINE
                else:
                    separator = PARAGRAPH if p_index else ""
                tokens = count(sentence)
                if tokens > max_tokens:
                    units.extend(_split_long(sentence, separator, max_tokens, count))
                else:
                    units.append(_Unit(sentence, tokens, separator))
    return units


def _overlap(units: list[_Unit], budget: int) -> list[_Unit]:
    """Letzte ganze Einheiten bis zum Budget, nie der ganze Chunk."""
    selected: list[_Unit] = []
    used = 0
    for unit in reversed(units[1:]):
        if used + unit.tokens > budget:
            break
        selected.insert(0, unit)
        used += unit.tokens
    return selected


def _paragraph_rest(units: list[_Unit]) -> list[int]:
    """Für jede Einheit: Tokens von ihr bis zum Ende ihres Absatzes."""
    rest = [0] * len(units)
    running = 0
    for index in range(len(units) - 1, -1, -1):
        running += units[index].tokens
        rest[index] = running
        if units[index].separator == PARAGRAPH:
            running = 0
    return rest


def _should_cut(
    tokens: int, unit: _Unit, rest_of_paragraph: int, target: float, max_tokens: int
) -> bool:
    """Schnitt vor `unit`? Bevorzugt an Absatzgrenzen, sonst an Satzgrenzen."""
    if tokens + unit.tokens > max_tokens:
        return True  # Höchstgrösse würde überschritten
    if unit.separator == PARAGRAPH:
        if tokens >= target:
            return True
        # Der nächste ganze Absatz passt nicht mehr: lieber hier an der Absatzgrenze schneiden.
        return tokens >= target * EARLY_PARAGRAPH_CUT and tokens + rest_of_paragraph > max_tokens
    # Mitten im Absatz nur schneiden, wenn sein Ende nicht mehr erreichbar ist.
    return tokens >= target and tokens + rest_of_paragraph > max_tokens


def _pack(units: list[_Unit], config: ChunkingConfig) -> list[tuple[list[_Unit], int]]:
    """Setzt Einheiten zu Chunks zusammen; liefert (Einheiten, Anzahl Overlap-Einheiten)."""
    total = sum(unit.tokens for unit in units)
    if total <= config.max_tokens:
        return [(units, 0)]
    target = total / math.ceil(total / config.target_tokens)  # ausgeglichene Zielgrösse
    rest = _paragraph_rest(units)

    chunks: list[tuple[list[_Unit], int]] = []
    current: list[_Unit] = []
    current_overlap = 0
    tokens = 0
    for index, unit in enumerate(units):
        if current and _should_cut(tokens, unit, rest[index], target, config.max_tokens):
            chunks.append((current, current_overlap))
            carry = _overlap(current, config.overlap_tokens)
            while carry and sum(u.tokens for u in carry) + unit.tokens > config.max_tokens:
                carry = carry[1:]
            current, current_overlap = list(carry), len(carry)
            tokens = sum(u.tokens for u in current)
        current.append(unit)
        tokens += unit.tokens
    chunks.append((current, current_overlap))
    return chunks


def _chunk_text(
    text: str, config: ChunkingConfig, count: TokenCounter
) -> list[tuple[str, int, dict[str, Any]]]:
    units = _units(text, config.max_tokens, count)
    packed = _pack(units, config)
    result = []
    for part, (chunk_units, overlap_count) in enumerate(packed, start=1):
        chunk_text = _render(chunk_units)
        overlap_chars = len(_render(chunk_units[:overlap_count]))
        metadata = {"part": part, "parts": len(packed), "overlap_chars": overlap_chars}
        result.append((chunk_text, count(chunk_text), metadata))
    return result


def _business_sections(document: DocumentData) -> list[tuple[str, str]]:
    pieces = _SECTION_HEADING.split(document.text)
    # pieces: [Text vor der ersten Überschrift, Überschrift, Text, Überschrift, Text, ...]
    sections = [(TITLE_SECTION[document.language], document.title)]
    if pieces[0].strip():
        sections.append(("", pieces[0].strip()))
    sections.extend(
        (pieces[i].strip(), pieces[i + 1].strip())
        for i in range(1, len(pieces) - 1, 2)
        if pieces[i + 1].strip()
    )
    return sections


def chunk_document(
    document: DocumentData,
    count_tokens: TokenCounter = approximate_token_count,
    config: ChunkingConfig | None = None,
) -> list[ChunkData]:
    """Chunks eines Dokuments in Reihenfolge, fortlaufend nummeriert."""
    config = config or ChunkingConfig()
    parts: list[tuple[str | None, str]]
    if document.source_type == "transcript":
        parts = [(None, document.text)]
    else:
        parts = [(section or None, body) for section, body in _business_sections(document)]

    chunks: list[ChunkData] = []
    for section, body in parts:
        for text, tokens, metadata in _chunk_text(body, config, count_tokens):
            if section is not None:
                metadata = {"section": section, **metadata}
            chunks.append(ChunkData(len(chunks), text, tokens, metadata))
    return chunks
