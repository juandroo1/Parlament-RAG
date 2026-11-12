"""Kontext-Header für das Embedding (plan.md, Abschnitt 5; Task 2.1)."""

import datetime as dt

import pytest

from ingest_fakes import PFAS_DAY, FixtureSource
from parlrag.index.chunker import ChunkData, chunk_document
from parlrag.index.header import MAX_TITLE_CHARS, context_header, embedding_text
from parlrag.ingest.mapping import DocumentData, Language
from parlrag.ingest.pipeline import collect_session

BOTH: frozenset[Language] = frozenset({"de", "fr"})
# Titel aus SubjectBusiness: Nummer, Art und Urheber des Vorstosses, dann der Titel.
PFAS_TITLE_START = "25.3866 Motion Michel Matthias. Einführung einer Deklarationspflicht für PFAS"


@pytest.fixture(scope="module")
def documents() -> dict[str, DocumentData]:
    source = FixtureSource()
    (session,) = source.sessions(PFAS_DAY, PFAS_DAY)
    batch = collect_session(source, session, PFAS_DAY, PFAS_DAY, BOTH)
    return {f"{d.source_id}-{d.language}": d for d in batch.documents}


def first_chunk(document: DocumentData, section: str | None = None) -> ChunkData:
    chunks = chunk_document(document)
    if section is None:
        return chunks[0]
    return next(c for c in chunks if c.metadata.get("section") == section)


def test_speech_header_in_german(documents: dict[str, DocumentData]) -> None:
    document = documents["418982-de"]
    header = context_header(document, first_chunk(document))
    assert header.startswith(
        f"Ständerat · 15.09.2026 · Michel Matthias (RL, ZG) · {PFAS_TITLE_START}"
    )


def test_federal_council_member_in_french(documents: dict[str, DocumentData]) -> None:
    document = documents["418840-fr"]
    header = context_header(document, first_chunk(document))
    assert header.startswith(
        "Conseil des Etats · 15.09.2026 · Baume-Schneider Elisabeth (Conseil fédéral) · 25.3866 "
    )


def test_business_headers_name_number_date_and_section(documents: dict[str, DocumentData]) -> None:
    german = documents["20253906-de"]
    assert context_header(german, first_chunk(german, "Eingereichter Text")) == (
        "Geschäft 25.3906 · eingereicht 20.06.2025 · "
        "PFAS-Grenzwerte mit realistischen Begleitmassnahmen · Eingereichter Text"
    )
    assert context_header(german, first_chunk(german)) == (
        "Geschäft 25.3906 · eingereicht 20.06.2025 · "
        "PFAS-Grenzwerte mit realistischen Begleitmassnahmen"
    )
    french = documents["20253906-fr"]
    assert context_header(french, first_chunk(french, "Avis du Conseil fédéral")).startswith(
        "Objet 25.3906 · déposé le 20.06.2025 · PFAS. Pour des valeurs limites"
    )


def test_missing_fields_are_left_out() -> None:
    document = DocumentData(
        source_type="transcript",
        source_id="1",
        language="de",
        title="Ratsdebatte",
        text="Text.",
        date=dt.date(2026, 3, 2),
        url="https://www.parlament.ch/de/x",
    )
    header = context_header(document, first_chunk(document))
    assert header == "02.03.2026 · Ratsdebatte"


def test_long_titles_are_shortened(documents: dict[str, DocumentData]) -> None:
    document = documents["418982-de"].model_copy(update={"title": "Wort " * 200})
    header = context_header(document, first_chunk(document))
    title = header.split(" · ")[-1]
    assert len(title) <= MAX_TITLE_CHARS
    assert title.endswith("…")


def test_embedding_text_with_and_without_header(documents: dict[str, DocumentData]) -> None:
    document = documents["418982-de"]
    chunk = first_chunk(document)

    with_header = embedding_text(document, chunk)
    without = embedding_text(document, chunk, with_header=False)

    assert with_header == f"{context_header(document, chunk)}\n\n{chunk.text}"
    assert without == chunk.text
