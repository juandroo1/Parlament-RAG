"""Goldset v1 (Task 3.1): Schema, Laden und Zusammensetzung von `golden.jsonl`."""

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from parlrag.evals import DEFAULT_GOLDEN_PATH, GoldenItem, GoldenSetError, load_golden

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN = REPO_ROOT / DEFAULT_GOLDEN_PATH


def _item(**changes: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "q01",
        "question": "Was sagte der Bundesrat zu den PFAS-Grenzwerten?",
        "language": "de",
        "expected_source_ids": ["transcript:418982", "business:20253906"],
        "answerable": True,
        "tags": ["teilkorpus"],
    }
    return base | changes


def test_valid_item() -> None:
    item = GoldenItem.model_validate(
        _item(filters={"council": "SR", "date_from": "2026-09-01"}, tags=["filter"], notes="x")
    )
    assert item.expected_source_ids == ("transcript:418982", "business:20253906")
    assert item.filters is not None and item.filters.council == "SR"
    assert item.has("filter") and not item.has("fr")


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"expected_source_ids": ["418982"]}, "Format der Quellen-ID"),
        ({"expected_source_ids": ["chunk:12"]}, "nur Dokumente, keine Chunks"),
        ({"expected_source_ids": []}, "beantwortbar ohne Quellen"),
        ({"answerable": False, "tags": ["unanswerable"]}, "unbeantwortbar mit Quellen"),
        ({"answerable": False, "expected_source_ids": []}, "Tag unanswerable fehlt"),
        ({"tags": ["unanswerable"]}, "Tag unanswerable bei beantwortbarer Frage"),
        (
            {"answerable": False, "expected_source_ids": [], "tags": ["unanswerable", "wertend"]},
            "wertend ist beantwortbar",
        ),
        ({"language": "fr"}, "Tag fr fehlt"),
        ({"tags": ["fr"]}, "Tag fr bei deutscher Frage"),
        ({"filters": {"council": "NR"}}, "Tag filter fehlt"),
        ({"tags": ["filter"]}, "Tag filter ohne Filter"),
        ({"filters": {}, "tags": ["filter"]}, "leere Filter"),
        ({"filters": {"council": "XX"}, "tags": ["filter"]}, "unbekannter Rat"),
        ({"tags": ["teilkorpus", "teilkorpus"]}, "Tag doppelt"),
        ({"tags": ["bogus"]}, "unbekannter Tag"),
        ({"expected_source_ids": ["business:1", "business:1"]}, "Quelle doppelt"),
        ({"language": "it"}, "Sprache"),
        ({"id": "x1"}, "ID-Format"),
        ({"extra": 1}, "unbekanntes Feld"),
    ],
)
def test_invalid_items_are_rejected(changes: dict[str, Any], reason: str) -> None:
    with pytest.raises(ValueError):
        GoldenItem.model_validate(_item(**changes))


def test_load_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "golden.jsonl"
    lines = [json.dumps(_item()), "", json.dumps(_item(id="q02"))]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert [item.id for item in load_golden(path)] == ["q01", "q02"]


@pytest.mark.parametrize(
    ("second_line", "message"),
    [
        (json.dumps(_item()), "Zeile 2: ID q01 doppelt"),
        ("{kein json", "Zeile 2"),
        (json.dumps(_item(id="q02", language="it")), "Zeile 2"),
    ],
)
def test_load_reports_line_numbers(tmp_path: Path, second_line: str, message: str) -> None:
    path = tmp_path / "golden.jsonl"
    path.write_text(json.dumps(_item()) + "\n" + second_line + "\n", encoding="utf-8")

    with pytest.raises(GoldenSetError, match=message):
        load_golden(path)


@pytest.fixture(scope="module")
def golden() -> list[GoldenItem]:
    return load_golden(GOLDEN)


def _category(item: GoldenItem) -> str:
    if item.has("unanswerable"):
        return "unbeantwortbar"
    if item.has("wertend"):
        return "wertend"
    return f"beantwortbar {item.language}"


def test_golden_composition(golden: list[GoldenItem]) -> None:
    """Zusammensetzung gemäss tasks.md, Task 3.1."""
    assert [item.id for item in golden] == [f"q{n:02d}" for n in range(1, 34)]
    assert Counter(_category(item) for item in golden) == {
        "beantwortbar de": 20,
        "beantwortbar fr": 5,
        "unbeantwortbar": 5,
        "wertend": 3,
    }
    crosslingual = [item for item in golden if item.has("crosslingual")]
    assert len(crosslingual) == 5
    assert all(item.answerable and not item.has("wertend") for item in crosslingual)
    assert sum(item.has("teilkorpus") for item in golden) >= 15
    assert not any(item.has("teilkorpus") and not item.answerable for item in golden)


def test_smoke_suite_covers_all_categories(golden: list[GoldenItem]) -> None:
    smoke = [item for item in golden if item.has("smoke")]
    assert len(smoke) == 15
    for tag in ("fr", "crosslingual", "filter", "unanswerable", "wertend", "teilkorpus"):
        assert any(item.has(tag) for item in smoke), tag
    assert any(not item.has("teilkorpus") and item.answerable for item in smoke)


def test_golden_sources_and_notes(golden: list[GoldenItem]) -> None:
    for item in golden:
        assert item.notes, f"{item.id}: Begründung fehlt"
        assert len(item.expected_source_ids) <= 5, f"{item.id}: zu breit"
    business_only = [
        item
        for item in golden
        if item.expected_source_ids
        and all(key.startswith("business:") for key in item.expected_source_ids)
    ]
    assert business_only, "Fragen, die nur Curia Vista beantwortet, fehlen"
