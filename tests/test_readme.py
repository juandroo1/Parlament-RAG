"""README (Task 6.2): Links, Anker und genannte Ergebnisdateien müssen existieren."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")

LINK = re.compile(r"\]\(([^)\s]+)\)")
RESULT_FILE = re.compile(r"`(evals/results/[^`<>…*]+\.(?:md|json))`")


def _slug(heading: str) -> str:
    """Anker wie bei GitHub: klein, ohne Satzzeichen, Leerzeichen als Bindestrich."""
    text = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return text.replace(" ", "-")


def _anchors() -> set[str]:
    return {_slug(line.lstrip("#")) for line in README.splitlines() if re.match(r"#{1,6} ", line)}


def test_relative_links_point_to_existing_files() -> None:
    targets = [link for link in LINK.findall(README) if not link.startswith(("http", "#"))]
    assert targets, "README ohne relative Links?"
    missing = [link for link in targets if not (ROOT / link.split("#")[0]).exists()]
    assert missing == []


def test_internal_anchors_exist() -> None:
    anchors = _anchors()
    links = [link[1:] for link in LINK.findall(README) if link.startswith("#")]
    assert links, "README ohne Inhaltsverzeichnis?"
    assert [link for link in links if link not in anchors] == []


def test_named_result_files_exist() -> None:
    files = RESULT_FILE.findall(README)
    assert len(files) >= 3
    assert [name for name in files if not (ROOT / name).exists()] == []


def test_readme_covers_portfolio_sections() -> None:
    anchors = _anchors()
    for section in (
        "architektur",
        "ergebnisse",
        "designentscheide",
        "kosten-und-latenz",
        "bekannte-grenzen",
        "arbeitsweise",
        "datenquelle-und-lizenz",
    ):
        assert section in anchors
    assert "```mermaid" in README
    assert "](docs/screenshot.png)" in README


def test_slug_matches_github() -> None:
    assert _slug(" Web-UI (Entwicklung)") == "web-ui-entwicklung"
    assert _slug(" Kosten und Latenz") == "kosten-und-latenz"
