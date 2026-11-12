import json
from pathlib import Path

import pytest

from parlrag.ingest.text import clean_markup

FIXTURES = Path(__file__).parent / "fixtures" / "odata"


def _rows(name: str) -> list[dict[str, object]]:
    data = json.loads((FIXTURES / name).read_text(encoding="utf-8"))["d"]
    rows = data["results"] if isinstance(data, dict) else data
    assert isinstance(rows, list)
    return rows


@pytest.mark.parametrize("raw", [None, "", "<pd_text></pd_text>", "<p>[VS]</p><p>[GZ]</p>"])
def test_empty_input_gives_empty_text(raw: str | None) -> None:
    assert clean_markup(raw) == ""


def test_paragraphs_become_blank_line_separated() -> None:
    raw = (
        "<pd_text><p>Erster Absatz.</p>\n"
        "<p>Zweiter <b>fetter</b> und <i>kursiver</i> Text.</p></pd_text>"
    )
    assert clean_markup(raw) == "Erster Absatz.\n\nZweiter fetter und kursiver Text."


def test_placeholders_are_removed_or_replaced() -> None:
    raw = "<p>am 5.[NB]März 2026 [GZ]</p><p>[VS] [PAGE 727] </p><p>[NAM][GZ]Ende</p>"
    assert clean_markup(raw) == "am 5. März 2026\n\nEnde"


def test_lists_become_bullet_lines_without_blank_lines_between_items() -> None:
    raw = (
        "<p>Der Bundesrat wird beauftragt:</p><p>&nbsp;</p>"
        '<ul style="list-style-type:disc;"><li>erstens;</li><li><p>zweitens</p></li></ul>'
        "<p>Schluss</p>"
    )
    assert (
        clean_markup(raw) == "Der Bundesrat wird beauftragt:\n\n- erstens;\n- zweitens\n\nSchluss"
    )


def test_entities_spans_and_line_breaks() -> None:
    raw = "<span><p><span>A &amp; B&nbsp;&laquo;C&raquo;</span><br>neue Zeile</p></span>"
    assert clean_markup(raw) == "A & B «C»\nneue Zeile"


def test_headings_are_kept_as_paragraphs() -> None:
    raw = '<h2 class="Titel_d"><strong>Medienmitteilung</strong></h2><p class="Standard_d">Text</p>'
    assert clean_markup(raw) == "Medienmitteilung\n\nText"


def test_all_transcript_fixtures_are_clean_and_idempotent() -> None:
    for row in _rows("transcript_subject82315_de.json"):
        cleaned = clean_markup(str(row["Text"]))
        assert "<" not in cleaned
        assert "[" not in cleaned
        assert "\n\n\n" not in cleaned
        assert clean_markup(cleaned) == cleaned


def test_business_fixture_texts_are_clean() -> None:
    (row,) = _rows("business_20253906_de.json")
    cleaned = clean_markup(str(row["SubmittedText"]))
    assert cleaned.startswith(
        "Der Bundesrat wird beauftragt, eine gesetzliche Grundlage zu schaffen"
    )
    assert "\n- " in cleaned
    assert "<" not in cleaned
    assert "&nbsp;" not in cleaned
