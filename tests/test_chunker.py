"""Chunker gemäss plan.md, Abschnitt 5: Grenzen, Overlap, Geschäftsabschnitte (Task 2.1)."""

import datetime as dt
import itertools
import math
import re
from typing import Any

import pytest

from ingest_fakes import PFAS_DAY, FixtureSource
from parlrag.index.chunker import (
    ChunkData,
    ChunkingConfig,
    approximate_token_count,
    chunk_document,
    split_sentences,
)
from parlrag.ingest.mapping import DocumentData, Language
from parlrag.ingest.pipeline import collect_session

CONFIG = ChunkingConfig(target_tokens=500, overlap_ratio=0.15)  # Höchstgrösse 600, Overlap 75
BOTH: frozenset[Language] = frozenset({"de", "fr"})


def speech(text: str, **overrides: Any) -> DocumentData:
    values: dict[str, Any] = {
        "source_type": "transcript",
        "source_id": "1",
        "language": "de",
        "title": "24.123 Ausbau der Bahninfrastruktur",
        "text": text,
        "council": "SR",
        "date": dt.date(2026, 9, 15),
        "url": "https://www.parlament.ch/de/x",
    }
    values.update(overrides)
    return DocumentData(**values)


def long_text(paragraphs: int, sentences: int = 5) -> str:
    return "\n\n".join(
        " ".join(
            f"Satz {p}.{s} enthält einige Wörter zur Debatte über den Verkehr im Land."
            for s in range(sentences)
        )
        for p in range(paragraphs)
    )


def words(text: str) -> list[str]:
    return text.split()


def expected_chunk_range(total_tokens: int) -> tuple[int, int]:
    """Schnitte an Absatzenden dürfen Chunks bis zur Höchstgrösse füllen."""
    return (
        math.ceil(total_tokens / CONFIG.max_tokens),
        math.ceil(total_tokens / CONFIG.target_tokens) + 1,
    )


def without_overlap(chunks: list[ChunkData]) -> str:
    return " ".join(chunk.text[chunk.metadata["overlap_chars"] :] for chunk in chunks)


@pytest.fixture(scope="module")
def fixture_documents() -> dict[str, DocumentData]:
    source = FixtureSource()
    (session,) = source.sessions(PFAS_DAY, PFAS_DAY)
    batch = collect_session(source, session, PFAS_DAY, PFAS_DAY, BOTH)
    return {f"{d.source_id}-{d.language}": d for d in batch.documents}


# --- Voten --------------------------------------------------------------------------


def test_config_derives_max_and_overlap() -> None:
    assert (CONFIG.max_tokens, CONFIG.overlap_tokens) == (600, 75)


def test_short_speech_stays_whole() -> None:
    text = "Ich danke der Kommission.\n\nWir stimmen zu."
    chunks = chunk_document(speech(text), config=CONFIG)

    assert chunks == [
        ChunkData(
            0, text, approximate_token_count(text), {"part": 1, "parts": 1, "overlap_chars": 0}
        )
    ]


def test_long_speech_respects_size_and_sentence_boundaries() -> None:
    text = long_text(paragraphs=30)
    total = approximate_token_count(text)

    chunks = chunk_document(speech(text), config=CONFIG)

    assert expected_chunk_range(total)[0] <= len(chunks) <= expected_chunk_range(total)[1]
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    for chunk in chunks:
        assert chunk.token_count <= CONFIG.max_tokens
        assert chunk.text.endswith(".")
        assert chunk.text[0].isupper()
        assert chunk.metadata["parts"] == len(chunks)


def test_overlap_repeats_whole_sentences_up_to_budget() -> None:
    chunks = chunk_document(speech(long_text(paragraphs=30)), config=CONFIG)

    assert chunks[0].metadata["overlap_chars"] == 0
    for previous, current in itertools.pairwise(chunks):
        overlap = current.metadata["overlap_chars"]
        assert overlap > 0
        repeated = current.text[:overlap]
        assert previous.text.endswith(repeated)
        assert repeated.startswith("Satz ") and repeated.endswith(".")
        assert approximate_token_count(repeated) <= CONFIG.overlap_tokens


def test_chunks_cover_the_whole_text_in_order() -> None:
    text = long_text(paragraphs=30)
    chunks = chunk_document(speech(text), config=CONFIG)
    assert words(without_overlap(chunks)) == words(text)


def test_prefers_paragraph_boundaries() -> None:
    text = long_text(paragraphs=30)
    chunks = chunk_document(speech(text), config=CONFIG)
    for chunk in chunks[:-1]:
        end = text.index(chunk.text) + len(chunk.text)
        assert text[end : end + 2] == "\n\n", "Chunk endet mitten im Absatz"


def test_sizes_are_balanced_without_tiny_rest() -> None:
    # Ein Absatz knapp über der Höchstgrösse: zwei etwa gleich grosse Chunks statt 600 + Rest.
    text = " ".join(f"Satz {i} handelt von der Finanzierung der Infrastruktur." for i in range(45))
    total = approximate_token_count(text)
    assert CONFIG.max_tokens < total < 2 * CONFIG.target_tokens

    chunks = chunk_document(speech(text), config=CONFIG)

    assert len(chunks) == 2
    assert min(c.token_count for c in chunks) >= total * 0.4


def test_overlong_sentence_is_split_at_word_boundaries() -> None:
    text = " ".join(f"Position{i}" for i in range(1500))  # ohne Satzzeichen, ca. 4000 Tokens

    chunks = chunk_document(speech(text), config=CONFIG)

    assert all(c.token_count <= CONFIG.max_tokens for c in chunks)
    assert words(without_overlap(chunks)) == words(text)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("Erster Satz. Zweiter Satz! Dritter?", ["Erster Satz.", "Zweiter Satz!", "Dritter?"]),
        (
            "Das gilt z. B. für Kantone. Neu ab 2027.",
            ["Das gilt z. B. für Kantone.", "Neu ab 2027."],
        ),
        (
            "Am 5. Oktober 2025 tagte er. Danach nicht.",
            ["Am 5. Oktober 2025 tagte er.", "Danach nicht."],
        ),
        ("Es kostet 3 Mio. Franken. Das ist viel.", ["Es kostet 3 Mio. Franken.", "Das ist viel."]),
        ("Gemäss Art. 5 BV gilt das. Punkt.", ["Gemäss Art. 5 BV gilt das.", "Punkt."]),
        ("M. Dupont l'a dit. Mme Martin aussi.", ["M. Dupont l'a dit.", "Mme Martin aussi."]),
        ("Er sagte: «Nein.» Dann ging er.", ["Er sagte: «Nein.»", "Dann ging er."]),
        ("ohne Satzende", ["ohne Satzende"]),
    ],
)
def test_split_sentences(line: str, expected: list[str]) -> None:
    assert split_sentences(line) == expected


def test_sentence_splitter_keeps_abbreviations_together() -> None:
    sentence = "Das betrifft z. B. die Kantone und ca. drei Viertel der Gemeinden. "
    chunks = chunk_document(speech(sentence * 60), config=CONFIG)
    for chunk in chunks:
        assert not re.search(r"(z\.|ca\.)$", chunk.text)
        assert chunk.text.startswith("Das betrifft")


def test_smaller_target_and_no_overlap_are_configurable() -> None:
    text = long_text(paragraphs=30)
    small = chunk_document(speech(text), config=ChunkingConfig(target_tokens=300))
    default = chunk_document(speech(text), config=CONFIG)
    no_overlap = chunk_document(speech(text), config=ChunkingConfig(overlap_ratio=0.0))

    assert len(small) > len(default)
    assert all(c.token_count <= 360 for c in small)
    assert all(c.metadata["overlap_chars"] == 0 for c in no_overlap)


def test_chunking_is_deterministic(fixture_documents: dict[str, DocumentData]) -> None:
    document = fixture_documents["418840-fr"]
    assert chunk_document(document, config=CONFIG) == chunk_document(document, config=CONFIG)


def test_longest_real_speech(fixture_documents: dict[str, DocumentData]) -> None:
    document = fixture_documents["418840-fr"]  # Baume-Schneider, rund 11'900 Zeichen
    total = approximate_token_count(document.text)

    chunks = chunk_document(document, config=CONFIG)

    assert expected_chunk_range(total)[0] <= len(chunks) <= expected_chunk_range(total)[1]
    assert all(c.token_count <= CONFIG.max_tokens for c in chunks)
    assert all(re.search(r"[.!?…»)]$", c.text) for c in chunks)
    assert words(without_overlap(chunks)) == words(document.text)


# --- Geschäfte ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("key", "sections"),
    [
        (
            "20253906-de",
            ["Titel", "Eingereichter Text", "Begründung", "Stellungnahme des Bundesrates"],
        ),
        ("20253906-fr", ["Titre", "Texte déposé", "Développement", "Avis du Conseil fédéral"]),
    ],
)
def test_business_has_title_chunk_and_one_chunk_group_per_section(
    fixture_documents: dict[str, DocumentData], key: str, sections: list[str]
) -> None:
    document = fixture_documents[key]

    chunks = chunk_document(document, config=CONFIG)

    assert chunks[0].text == document.title
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    seen = list(dict.fromkeys(c.metadata["section"] for c in chunks))
    assert seen == sections
    assert not any("## " in c.text for c in chunks)
    for section in sections[1:]:
        assert not any(c.text.startswith(section) for c in chunks)


def test_long_business_section_is_split(fixture_documents: dict[str, DocumentData]) -> None:
    document = fixture_documents["20253906-de"]
    chunks = chunk_document(document, config=ChunkingConfig(target_tokens=100))

    response = [c for c in chunks if c.metadata["section"] == "Stellungnahme des Bundesrates"]
    assert len(response) > 1
    assert [c.metadata["part"] for c in response] == list(range(1, len(response) + 1))
    assert all(c.token_count <= 120 for c in response)
