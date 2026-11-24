"""Hinweise zur Erkennung für `parlrag search` und `parlrag ask` (Spec 003, Task 8.4)."""

from collections.abc import Sequence

from parlrag.query.resolve import Coverage
from parlrag.query.speakers import Speaker
from parlrag.retrieval.filters import SearchFilters


def speaker_label(speaker: Speaker) -> str:
    """«Müller Damian (RL, LU)» bzw. «Rösti Albert (Bundesrat)»."""
    if speaker.federal_council:
        return f"{speaker.name} (Bundesrat)"
    details = ", ".join(part for part in (speaker.parl_group, speaker.canton) if part)
    return f"{speaker.name} ({details})" if details else speaker.name


def detection_notes(
    filters: SearchFilters,
    detected: Sequence[str],
    speaker_candidates: Sequence[Speaker],
    coverage: Coverage | None,
    retried_without: Sequence[str],
    out_of_range: bool = False,
) -> list[str]:
    notes = []
    if detected:
        values = filters.model_dump(mode="json")
        notes.append(
            "Aus der Frage erkannt: " + ", ".join(f"{key}={values[key]}" for key in detected)
        )
    if speaker_candidates:
        notes.append(
            "Name mehrdeutig, ohne Personenfilter gesucht. Gemeint? "
            + " · ".join(speaker_label(s) for s in speaker_candidates)
        )
    if "speaker" in retried_without:
        notes.append(
            "Zur erkannten Person gab es keine passenden Voten; gesucht wurde ohne Personenfilter."
        )
    if coverage is not None and (out_of_range or coverage.partial):
        span = f"{coverage.first:%d.%m.%Y} bis {coverage.last:%d.%m.%Y}"
        if out_of_range:
            notes.append(f"Zeitraum ausserhalb der Daten (Voten vom {span}); keine Suche.")
        else:
            notes.append(f"Die Voten reichen vom {span}; der Zeitraum geht darüber hinaus.")
    return notes
