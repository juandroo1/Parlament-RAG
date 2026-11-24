"""Erkannte und gesetzte Filter zusammenführen, Datenbestand prüfen (Spec 003, plan.md Abschnitt 7).

- Gesetzte Filter haben Vorrang (AK-17.2): Ein gesetzter Zeitraum (`date_from` oder `date_to`)
  ersetzt den erkannten ganz, eine gesetzte Person die erkannte.
- Datenbestand (AK-16.1 bis AK-16.3): Liegt der Zeitraum ganz ausserhalb der Voten im Katalog,
  ist `out_of_range` gesetzt; überlappt er nur teilweise, `coverage.partial`. Das gilt auch für
  gesetzte Filter.
"""

import datetime as dt
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from parlrag.query.catalog import Catalog, load_catalog
from parlrag.query.detect import Detection, detect
from parlrag.query.speakers import Speaker
from parlrag.retrieval.filters import SearchFilters

logger = logging.getLogger(__name__)

EMPTY_CATALOG = Catalog(first=None, last=None, sessions=(), speakers=())


@dataclass(frozen=True)
class Coverage:
    """Zeitraum der Voten im Korpus; `partial`, wenn der gefragte Zeitraum darüber hinausgeht."""

    first: dt.date
    last: dt.date
    partial: bool = False


@dataclass(frozen=True)
class Resolution:
    filters: SearchFilters  # angewandt: gesetzt plus erkannt
    detected: tuple[str, ...] = ()  # erkannte Filter: "speaker", "date_from", "date_to"
    speaker_candidates: tuple[Speaker, ...] = ()
    coverage: Coverage | None = None
    out_of_range: bool = False

    @property
    def speaker_detected(self) -> bool:
        return "speaker" in self.detected


def _coverage(filters: SearchFilters, catalog: Catalog) -> tuple[Coverage | None, bool]:
    """(Abdeckung, ganz ausserhalb). Ohne Voten im Katalog keine Aussage."""
    if catalog.first is None or catalog.last is None:
        return None, False
    start, end = filters.date_from, filters.date_to
    if start is None and end is None:
        return Coverage(catalog.first, catalog.last), False
    outside = (end is not None and end < catalog.first) or (
        start is not None and start > catalog.last
    )
    partial = not outside and (
        (start is not None and start < catalog.first) or (end is not None and end > catalog.last)
    )
    return Coverage(catalog.first, catalog.last, partial=partial), outside


def resolve(
    question: str,
    filters: SearchFilters | None,
    catalog: Catalog,
    today: dt.date,
    *,
    detection: bool = True,
) -> Resolution:
    filters = filters or SearchFilters()
    found = detect(question, catalog, today) if detection else Detection()
    update: dict[str, object] = {}
    detected: list[str] = []
    if found.speaker is not None and filters.speaker is None:
        update["speaker"] = found.speaker.name
        detected.append("speaker")
    if found.period is not None and filters.date_from is None and filters.date_to is None:
        period = found.period
        for key, value in (("date_from", period.date_from), ("date_to", period.date_to)):
            if value is not None:
                update[key] = value
                detected.append(key)
    applied = filters.model_copy(update=update) if update else filters
    coverage, outside = _coverage(applied, catalog)
    candidates = found.speaker_candidates if filters.speaker is None else ()
    return Resolution(
        filters=applied,
        detected=tuple(detected),
        speaker_candidates=candidates,
        coverage=coverage,
        out_of_range=outside,
    )


class CatalogCache:
    """Katalog aus der Datenbank, höchstens `ttl_s` Sekunden alt (plan.md, Abschnitt 3).

    Ist die Datenbank nicht erreichbar, bleibt der letzte Katalog (oder ein leerer) gültig: Die
    Suche läuft dann ohne Erkennung weiter, statt abzubrechen."""

    def __init__(
        self,
        engine: Engine,
        ttl_s: float = 600.0,
        clock: Callable[[], float] = time.monotonic,
        loader: Callable[[Engine], Catalog] | None = None,
    ) -> None:
        self.engine = engine
        self.ttl_s = ttl_s
        self.clock = clock
        self.loader = loader or _load
        self._catalog: Catalog | None = None
        self._loaded_at = 0.0
        self._lock = threading.Lock()

    def get(self) -> Catalog:
        with self._lock:
            now = self.clock()
            if self._catalog is None or now - self._loaded_at >= self.ttl_s:
                try:
                    self._catalog = self.loader(self.engine)
                except SQLAlchemyError:
                    logger.exception("Katalog nicht ladbar; Erkennung vorerst ohne Katalog")
                    self._catalog = self._catalog or EMPTY_CATALOG
                self._loaded_at = now
            return self._catalog


def _load(engine: Engine) -> Catalog:
    with engine.connect() as connection:
        return load_catalog(connection)
