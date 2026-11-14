"""`parlrag search` (Task 2.5): Ausgabe und Optionen, mit ersetztem Retriever."""

import dataclasses
import datetime as dt
import json
import uuid
from typing import Any

import pytest
from typer.testing import CliRunner

from fakes import FakeEmbedder
from parlrag import cli
from parlrag.retrieval import RetrievalConfig, SearchFilters, SearchHit
from parlrag.retrieval.formatting import format_hit, snippet

runner = CliRunner()

SPEECH = SearchHit(
    chunk_id=uuid.UUID(int=1),
    document_id=uuid.UUID(int=2),
    chunk_index=0,
    text="Die Problematik und das bisher unterschätzte Risiko dieser PFAS-Substanzen sind bekannt.",
    section=None,
    score=0.0325,
    rank=1,
    fulltext_rank=3,
    fulltext_score=0.4,
    vector_rank=1,
    vector_similarity=0.571,
    source_type="transcript",
    source_id="418982",
    language="de",
    title="25.3866 Motion Michel Matthias. Einführung einer Deklarationspflicht für PFAS",
    speaker_name="Michel Matthias",
    parl_group="RL",
    canton="ZG",
    council="SR",
    date=dt.date(2026, 9, 15),
    debate_dates=(),
    debate_councils=(),
    business_numbers=("25.3866", "25.3902", "25.3906"),
    url="https://www.parlament.ch/de/ratsbetrieb/amtliches-bulletin/"
    "amtliches-bulletin-die-verhandlungen?SubjectId=82315#votum6",
)
BUSINESS = SearchHit(
    chunk_id=uuid.UUID(int=3),
    document_id=uuid.UUID(int=4),
    chunk_index=2,
    text="Der Bundesrat beantragt die Ablehnung der Motion. " * 10,
    section="Stellungnahme des Bundesrates",
    score=0.0164,
    rank=2,
    fulltext_rank=None,
    fulltext_score=None,
    vector_rank=2,
    vector_similarity=0.55,
    source_type="business",
    source_id="20253906",
    language="de",
    title="PFAS-Grenzwerte mit realistischen Begleitmassnahmen",
    speaker_name=None,
    parl_group=None,
    canton=None,
    council=None,
    date=dt.date(2025, 6, 20),
    debate_dates=(dt.date(2026, 9, 15),),
    debate_councils=("SR",),
    business_numbers=("25.3906",),
    url="https://www.parlament.ch/de/ratsbetrieb/suche-curia-vista/geschaeft?AffairId=20253906",
)


class FakeRetriever:
    def __init__(self, hits: list[SearchHit]) -> None:
        self.hits = hits
        self.calls: list[dict[str, Any]] = []
        self.embedder = FakeEmbedder()
        self.config = RetrievalConfig()

    def search(
        self, query: str, filters: SearchFilters | None = None, *, mode: str, top_n: int
    ) -> list[SearchHit]:
        self.calls.append({"query": query, "filters": filters, "mode": mode, "top_n": top_n})
        return self.hits[:top_n]


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeRetriever:
    retriever = FakeRetriever([SPEECH, BUSINESS])
    monkeypatch.setattr(cli, "build_retriever", lambda: retriever)
    return retriever


def test_source_key_uses_goldset_format() -> None:
    assert SPEECH.source_key == "transcript:418982"
    assert BUSINESS.source_key == "business:20253906"


def test_speech_shows_citation_metadata() -> None:
    head, meta, text, url = format_hit(SPEECH)
    assert head.startswith(" 1. transcript:418982 [de]")
    assert "Volltext #3" in head and "Vektor #1 (0.57)" in head
    assert (
        meta.strip()
        == "Michel Matthias (RL, ZG) · Ständerat · 15.09.2026 · 25.3866, 25.3902, 25.3906"
    )
    assert text.strip().startswith("«Die Problematik")
    assert url.strip().endswith("#votum6")


def test_business_shows_section_and_debates() -> None:
    head, meta, text, _ = format_hit(BUSINESS)
    assert "Volltext" not in head
    assert meta.strip() == (
        "Geschäft 25.3906 · Stellungnahme des Bundesrates · Debatten 15.09.2026 (SR)"
    )
    assert text.strip().endswith("…»")


def test_federal_council_member_is_labelled_not_shown_with_canton() -> None:
    baume_schneider = dataclasses.replace(
        SPEECH,
        speaker_name="Baume-Schneider Elisabeth",
        parl_group=None,
        canton="JU",
        speaker_function="BR-F",
    )
    meta = format_hit(baume_schneider)[1].strip()
    assert meta.startswith("Baume-Schneider Elisabeth (Bundesrat) · Ständerat")


def test_model_load_is_reported_separately(fake: FakeRetriever) -> None:
    hybrid = runner.invoke(cli.app, ["search", "PFAS"])
    fulltext = runner.invoke(cli.app, ["search", "PFAS", "--mode", "fulltext"])

    assert "Modell vorher geladen in" in hybrid.output
    assert "Modell vorher geladen" not in fulltext.output
    assert fake.embedder.calls == 1  # nur der hybride Aufruf lädt das Modell vor


def test_snippet_is_single_line_and_shortened() -> None:
    assert snippet("eins\n\nzwei") == "«eins zwei»"
    long = snippet("Wort " * 100)
    assert len(long) <= 202 and long.endswith(" …»")


def test_search_prints_hits_and_passes_options(fake: FakeRetriever) -> None:
    result = runner.invoke(
        cli.app,
        [
            "search",
            "Was sagte der Ständerat zu PFAS?",
            "--mode",
            "vector",
            "--top",
            "5",
            "--council",
            "SR",
            "--date-from",
            "2026-09-01",
            "--date-to",
            "2026-09-30",
            "--parl-group",
            "RL",
        ],
    )

    assert result.exit_code == 0, result.output
    (call,) = fake.calls
    assert call["mode"] == "vector" and call["top_n"] == 5
    assert call["filters"] == SearchFilters(
        council="SR", date_from=dt.date(2026, 9, 1), date_to=dt.date(2026, 9, 30), parl_group="RL"
    )
    assert "Suche (vector) «Was sagte der Ständerat zu PFAS?»" in result.output
    assert "council=SR" in result.output and "parl_group=RL" in result.output
    assert "transcript:418982" in result.output
    assert "business:20253906" in result.output


def test_defaults_are_configured_mode_top_10_without_filters(fake: FakeRetriever) -> None:
    result = runner.invoke(cli.app, ["search", "PFAS"])
    assert result.exit_code == 0, result.output
    assert fake.calls[0]["mode"] == "vector"
    assert fake.calls[0]["top_n"] == 10
    assert fake.calls[0]["filters"] == SearchFilters()


def test_json_output_contains_all_fields(fake: FakeRetriever) -> None:
    result = runner.invoke(cli.app, ["search", "PFAS", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["query"] == "PFAS" and payload["mode"] == "vector"
    assert [hit["source_key"] for hit in payload["hits"]] == [
        "transcript:418982",
        "business:20253906",
    ]
    assert payload["hits"][0]["speaker_name"] == "Michel Matthias"
    assert payload["hits"][1]["debate_dates"] == ["2026-09-15"]


def test_no_hits_prints_a_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "build_retriever", lambda: FakeRetriever([]))
    result = runner.invoke(cli.app, ["search", "Quantenchromodynamik"])
    assert result.exit_code == 0
    assert "0 Treffer" in result.output and "Keine Treffer" in result.output


@pytest.mark.parametrize(
    "args",
    [
        ["--council", "XY"],
        ["--date-from", "2026-09-30", "--date-to", "2026-09-01"],
        ["--date-from", "30.09.2026"],
        ["--top", "0"],
        ["--mode", "magic"],
    ],
)
def test_invalid_options_are_rejected(fake: FakeRetriever, args: list[str]) -> None:
    result = runner.invoke(cli.app, ["search", "PFAS", *args])
    assert result.exit_code == 2
    assert fake.calls == []


def test_configured_mode_is_used_when_option_is_missing(fake: FakeRetriever) -> None:
    fake.config = RetrievalConfig(mode="hybrid")
    runner.invoke(cli.app, ["search", "PFAS"])
    runner.invoke(cli.app, ["search", "PFAS", "--mode", "fulltext"])

    assert [call["mode"] for call in fake.calls] == ["hybrid", "fulltext"]
