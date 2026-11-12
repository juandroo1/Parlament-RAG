"""Volltext, Vektor, RRF und Filter gegen `parlrag_test` (Task 2.4; AK-4.1 bis AK-4.3)."""

import datetime as dt

import pytest
from pydantic import ValidationError
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from fakes import FakeEmbedder
from ingest_fakes import PFAS_DAY, FixtureSource
from parlrag.db.models import Chunk, Document
from parlrag.index.indexer import IndexConfig, index_documents
from parlrag.ingest.mapping import Language
from parlrag.ingest.pipeline import run_ingest
from parlrag.retrieval import RetrievalConfig, Retriever, SearchFilters, SearchHit
from parlrag.retrieval.fulltext import detect_query_language, strip_function_words

pytestmark = pytest.mark.db

BOTH: frozenset[Language] = frozenset({"de", "fr"})
MICHEL_CHUNK_START = "Die Problematik und das bisher unterschätzte Risiko"


@pytest.fixture
def indexed(empty_db: Engine) -> tuple[Engine, FakeEmbedder]:
    run_ingest(FixtureSource(), sessionmaker(empty_db), PFAS_DAY, PFAS_DAY, BOTH)
    embedder = FakeEmbedder()
    index_documents(empty_db, embedder, IndexConfig(model_name="fake/model"))
    return empty_db, embedder


def retriever(indexed: tuple[Engine, FakeEmbedder], **config: int) -> Retriever:
    return Retriever(indexed[0], FakeEmbedder(), RetrievalConfig(**config))


def embedding_text_of(indexed: tuple[Engine, FakeEmbedder], chunk_start: str) -> str:
    """Der Text, mit dem ein Chunk eingebettet wurde (Header + Chunk)."""
    return next(t for t in indexed[1].texts if t.split("\n\n", 1)[1].startswith(chunk_start))


def satisfies(hit: SearchHit, filters: SearchFilters) -> bool:
    """Referenz-Logik von AK-4.2/AK-4.3 in Python."""
    if hit.source_type == "transcript":
        dates_ok = (
            (filters.date_from or dt.date.min) <= hit.date <= (filters.date_to or dt.date.max)
        )
        return (
            (filters.council is None or hit.council == filters.council)
            and ((filters.date_from is None and filters.date_to is None) or dates_ok)
            and (filters.parl_group is None or hit.parl_group == filters.parl_group)
        )
    in_range = any(
        (filters.date_from or dt.date.min) <= day <= (filters.date_to or dt.date.max)
        for day in hit.debate_dates
    )
    return (
        (filters.council is None or filters.council in hit.debate_councils)
        and ((filters.date_from is None and filters.date_to is None) or in_range)
        and filters.parl_group is None
    )


# --- Volltext ------------------------------------------------------------------------


def test_fulltext_finds_german_terms_without_loading_a_model(
    indexed: tuple[Engine, FakeEmbedder],
) -> None:
    search = retriever(indexed)
    hits = search.search("Deklarationspflicht für PFAS", mode="fulltext")

    assert hits
    assert all(hit.fulltext_rank is not None and hit.vector_rank is None for hit in hits)
    assert "PFAS" in hits[0].text
    assert search.embedder.calls == 0  # type: ignore[attr-defined]


def test_fulltext_uses_french_stemming_for_french_chunks(
    indexed: tuple[Engine, FakeEmbedder],
) -> None:
    hits = retriever(indexed).search("valeurs limites réalistes", mode="fulltext")
    assert hits
    assert hits[0].language == "fr"


def test_fulltext_combines_terms_with_or(indexed: tuple[Engine, FakeEmbedder]) -> None:
    hits = retriever(indexed).search("PFAS Quantenchromodynamik", mode="fulltext")
    assert hits  # das unbekannte Wort verhindert keinen Treffer


@pytest.mark.parametrize("query", ["und der die das", "le la les des et"])
def test_fulltext_with_only_stopwords_finds_nothing(
    indexed: tuple[Engine, FakeEmbedder], query: str
) -> None:
    assert retriever(indexed).search(query, mode="fulltext") == []


def test_german_question_still_finds_proper_names_in_french_chunks(
    indexed: tuple[Engine, FakeEmbedder],
) -> None:
    hits = retriever(indexed).search("Was sagte die Bundesrätin zu PFAS?", mode="fulltext")
    assert "fr" in {hit.language for hit in hits}


@pytest.mark.parametrize(
    ("query", "language"),
    [
        ("Welche Argumente wurden im Ständerat zum Ausbau der Bahn vorgebracht?", "de"),
        ("Quels arguments ont été avancés au Conseil des Etats sur les PFAS ?", "fr"),
        ("PFAS", None),
    ],
)
def test_detect_query_language(query: str, language: str | None) -> None:
    assert detect_query_language(query) == language


def test_strip_function_words_keeps_content_words() -> None:
    assert strip_function_words("Was sagte die Bundesrätin zu PFAS?").split() == [
        "sagte",
        "Bundesrätin",
        "zu",
        "PFAS?",
    ]
    assert strip_function_words("les valeurs limites des PFAS").split() == [
        "valeurs",
        "limites",
        "PFAS",
    ]


# --- Vektor und Hybrid -----------------------------------------------------------------


def test_vector_search_ranks_identical_text_first(indexed: tuple[Engine, FakeEmbedder]) -> None:
    query = embedding_text_of(indexed, MICHEL_CHUNK_START)
    hits = retriever(indexed).search(query, mode="vector")

    assert hits[0].text.startswith(MICHEL_CHUNK_START)
    assert hits[0].vector_similarity == pytest.approx(1.0, abs=1e-5)
    assert hits[0].fulltext_rank is None


def test_hybrid_puts_hits_from_both_lists_first(indexed: tuple[Engine, FakeEmbedder]) -> None:
    query = embedding_text_of(indexed, MICHEL_CHUNK_START)
    hits = retriever(indexed).search(query)

    top = hits[0]
    assert top.text.startswith(MICHEL_CHUNK_START)
    assert top.vector_rank == 1 and top.fulltext_rank is not None
    assert top.score == pytest.approx(1 / 61 + 1 / (60 + top.fulltext_rank))
    assert [hit.rank for hit in hits] == list(range(1, len(hits) + 1))
    assert len(hits) <= 20


def test_hits_carry_citation_metadata(indexed: tuple[Engine, FakeEmbedder]) -> None:
    query = embedding_text_of(indexed, MICHEL_CHUNK_START)
    top = retriever(indexed).search(query, mode="vector")[0]

    assert (top.speaker_name, top.parl_group, top.council) == ("Michel Matthias", "RL", "SR")
    assert top.date == PFAS_DAY
    assert top.business_numbers == ("25.3866", "25.3902", "25.3906")
    assert top.url.endswith("SubjectId=82315#votum6")


# --- Filter (AK-4.1 bis AK-4.3) -----------------------------------------------------------

FILTERS = [
    SearchFilters(council="SR"),
    SearchFilters(council="NR"),
    SearchFilters(date_from=dt.date(2026, 9, 16)),
    SearchFilters(date_from=dt.date(2026, 9, 1), date_to=dt.date(2026, 9, 30)),
    SearchFilters(parl_group="RL"),
    SearchFilters(parl_group="M-E", council="SR"),
]


@pytest.mark.parametrize("filters", FILTERS, ids=lambda f: str(f.sql_params()))
@pytest.mark.parametrize("mode", ["hybrid", "fulltext", "vector"])
def test_every_hit_satisfies_the_filter(
    indexed: tuple[Engine, FakeEmbedder], filters: SearchFilters, mode: str
) -> None:
    hits = retriever(indexed).search("PFAS Grenzwerte Kantone", filters, mode=mode)  # type: ignore[arg-type]
    assert all(satisfies(hit, filters) for hit in hits)


def test_council_and_date_filters_select_expected_documents(
    indexed: tuple[Engine, FakeEmbedder],
) -> None:
    search = retriever(indexed)
    query = "PFAS Grenzwerte Kantone"
    assert search.search(query, SearchFilters(council="NR"), mode="vector") == []
    assert search.search(query, SearchFilters(date_from=dt.date(2026, 9, 16)), mode="vector") == []
    sr = search.search(query, SearchFilters(council="SR"), mode="vector")
    assert {hit.source_type for hit in sr} == {"transcript", "business"}


def test_parl_group_filter_excludes_businesses(indexed: tuple[Engine, FakeEmbedder]) -> None:
    hits = retriever(indexed).search("PFAS", SearchFilters(parl_group="RL"), mode="vector")
    assert hits
    assert {hit.source_type for hit in hits} == {"transcript"}
    assert {hit.speaker_name for hit in hits} == {"Michel Matthias"}


def test_filters_apply_before_the_search(indexed: tuple[Engine, FakeEmbedder]) -> None:
    """AK-4.1: Mit nur 2 Kandidaten liefert die gefilterte Suche trotzdem 2 passende Chunks,
    obwohl diese ungefiltert nicht unter den Top 2 wären."""
    engine = indexed[0]
    with Session(engine) as db:
        rl_chunks = db.scalar(
            select(func.count())
            .select_from(Chunk)
            .join(Document)
            .where(Document.parl_group == "RL")
        )
    assert rl_chunks is not None and rl_chunks >= 2

    search = retriever(indexed, candidates=2)
    query = embedding_text_of(indexed, "La question des PFAS")  # Chunk der Bundesrätin
    unfiltered = search.search(query, mode="vector")
    filtered = search.search(query, SearchFilters(parl_group="RL"), mode="vector")

    assert all(hit.parl_group != "RL" for hit in unfiltered[:1])
    assert len(filtered) == 2
    assert all(hit.parl_group == "RL" for hit in filtered)


def test_invalid_date_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SearchFilters(date_from=dt.date(2026, 9, 30), date_to=dt.date(2026, 9, 1))
