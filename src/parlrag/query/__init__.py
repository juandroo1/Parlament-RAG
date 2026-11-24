"""Person und Zeitraum aus der Frage (Spec 003): Personenliste, Katalog und Erkennung."""

from parlrag.query.catalog import Catalog, Session, load_catalog
from parlrag.query.detect import Detection, detect
from parlrag.query.speakers import FEDERAL_COUNCIL_FUNCTIONS, Speaker, list_speakers
from parlrag.query.time import Period

__all__ = [
    "FEDERAL_COUNCIL_FUNCTIONS",
    "Catalog",
    "Detection",
    "Period",
    "Session",
    "Speaker",
    "detect",
    "list_speakers",
    "load_catalog",
]
