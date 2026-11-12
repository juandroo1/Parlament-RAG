"""Textbereinigung für Voten und Geschäftstexte (plan.md, Abschnitt 3; Entscheidungsprotokoll).

- HTML-artiges Markup (`<pd_text>`, `<p>`, `<b>`, `<ul>`, `<li>`, `<span>`, `<h2>` …) wird
  mit dem HTML-Parser der Standardbibliothek entfernt, Absätze bleiben erhalten.
- Platzhalter des Amtlichen Bulletins: `[NB]` wird zu einem Leerzeichen, `[GZ]`, `[VS]`,
  `[NAM]` und `[PAGE n]` fallen weg.
- HTML-Entities werden aufgelöst, Leerraum wird normalisiert.
"""

import re
from html.parser import HTMLParser

_DROPPED_PLACEHOLDERS = re.compile(r"\[(?:GZ|VS|NAM|PAGE\s*\d+)\]")
_BLOCK_TAGS = frozenset(
    {"p", "div", "pd_text", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "table", "tr"}
)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._li_depth = 0

    def _block_break(self) -> None:
        # Innerhalb eines Listenpunkts (z. B. <li><p>…</p></li>) kein Absatz, nur ein Leerzeichen.
        self.parts.append(" " if self._li_depth else "\n\n")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br":
            self.parts.append("\n")
        elif tag == "li":
            self._li_depth += 1
            self.parts.append("\n- ")
        elif tag in ("ul", "ol"):
            self.parts.append("\n\n")
        elif tag in _BLOCK_TAGS:
            self._block_break()

    def handle_endtag(self, tag: str) -> None:
        if tag == "li":
            self._li_depth = max(0, self._li_depth - 1)
        elif tag in ("ul", "ol"):
            self.parts.append("\n\n")
        elif tag in _BLOCK_TAGS:
            self._block_break()

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _normalize_whitespace(text: str) -> str:
    text = text.replace(chr(0xA0), " ")  # geschütztes Leerzeichen
    lines = [re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_markup(raw: str | None) -> str:
    """Bereinigter Klartext mit Absätzen (Leerzeile) und Listenpunkten («- »)."""
    if not raw:
        return ""
    text = raw.replace("[NB]", " ")
    text = _DROPPED_PLACEHOLDERS.sub("", text)
    extractor = _TextExtractor()
    extractor.feed(text)
    extractor.close()
    return _normalize_whitespace("".join(extractor.parts))
