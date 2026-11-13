"""Ausgabe von Suchtreffern für `parlrag search` (Text und JSON)."""

import dataclasses
import json
from collections.abc import Sequence
from typing import Any

from parlrag.retrieval.filters import SearchFilters
from parlrag.retrieval.retriever import SearchHit

COUNCIL_NAMES = {"NR": "Nationalrat", "SR": "Ständerat", "V": "Vereinigte Bundesversammlung"}
SNIPPET_CHARS = 200


def _date(value: Any) -> str:
    return str(value.strftime("%d.%m.%Y"))


def snippet(text: str, limit: int = SNIPPET_CHARS) -> str:
    flat = " ".join(text.split())
    if len(flat) <= limit:
        return f"«{flat}»"
    return f"«{flat[: limit - 1].rsplit(' ', 1)[0]} …»"


def format_hit(hit: SearchHit) -> list[str]:
    """Vier Zeilen: Rang und Scores, Metadaten, Ausschnitt, Link."""
    scores = [f"score {hit.score:.4f}"]
    if hit.fulltext_rank is not None:
        scores.append(f"Volltext #{hit.fulltext_rank}")
    if hit.vector_rank is not None:
        scores.append(f"Vektor #{hit.vector_rank} ({hit.vector_similarity or 0:.2f})")
    head = f"{hit.rank:>2}. {hit.source_key} [{hit.language}]  " + " · ".join(scores)

    if hit.source_type == "transcript":
        speaker = hit.speaker_name or "unbekannt"
        if hit.parl_group:
            details = ", ".join(part for part in (hit.parl_group, hit.canton) if part)
        elif hit.speaker_function and hit.speaker_function.startswith("BR"):
            details = "Bundesrat"
        else:
            details = ""
        parts = [f"{speaker} ({details})" if details else speaker]
        if hit.council:
            parts.append(COUNCIL_NAMES.get(hit.council, hit.council))
        parts.append(_date(hit.date))
        if hit.business_numbers:
            parts.append(", ".join(hit.business_numbers))
    else:
        number = hit.business_numbers[0] if hit.business_numbers else hit.source_id
        parts = [f"Geschäft {number}"]
        if hit.section:
            parts.append(hit.section)
        if hit.debate_dates:
            dates = ", ".join(_date(day) for day in hit.debate_dates)
            parts.append(f"Debatten {dates} ({', '.join(hit.debate_councils)})")
    return [head, "    " + " · ".join(parts), "    " + snippet(hit.text), "    " + hit.url]


def format_results(
    query: str,
    mode: str,
    filters: SearchFilters,
    hits: Sequence[SearchHit],
    duration_ms: float,
    model_load_ms: float | None = None,
) -> str:
    active = filters.model_dump(exclude_none=True, mode="json")
    header = f"Suche ({mode}) «{query}»"
    if active:
        header += " · Filter " + ", ".join(f"{key}={value}" for key, value in active.items())
    header += f" · {len(hits)} Treffer in {duration_ms:.0f} ms"
    if model_load_ms is not None:
        header += f" (Modell vorher geladen in {model_load_ms / 1000:.1f} s)"
    if not hits:
        return (
            header
            + "\nKeine Treffer. Andere Begriffe, einen anderen Modus oder weniger Filter versuchen."
        )
    lines = [header]
    for hit in hits:
        lines.append("")
        lines.extend(format_hit(hit))
    return "\n".join(lines)


def results_json(
    query: str,
    mode: str,
    filters: SearchFilters,
    hits: Sequence[SearchHit],
    duration_ms: float,
    model_load_ms: float | None = None,
) -> str:
    payload = {
        "query": query,
        "mode": mode,
        "filters": filters.model_dump(exclude_none=True, mode="json"),
        "duration_ms": round(duration_ms, 1),
        "model_load_ms": round(model_load_ms, 1) if model_load_ms is not None else None,
        "hits": [{"source_key": hit.source_key, **dataclasses.asdict(hit)} for hit in hits],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)
