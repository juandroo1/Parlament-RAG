"""`GET /speakers`: Personen mit Voten für die Vorschläge im Filter «Person» (Spec 003, AK-18.1)."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from parlrag.api.ask import ERROR_CODE_HEADER
from parlrag.db.session import get_engine
from parlrag.query import Speaker, list_speakers

logger = logging.getLogger(__name__)

router = APIRouter()

# Die Liste ändert sich nur mit einem neuen Ingest; Browser und Proxys dürfen sie 10 Minuten halten.
CACHE_CONTROL = "public, max-age=600"


@router.get("/speakers", response_model=list[Speaker])
def speakers(response: Response, engine: Annotated[Engine, Depends(get_engine)]) -> list[Speaker]:
    """Alle Personen mit Voten, alphabetisch; `name` ist der Wert für den Filter `speaker`."""
    try:
        with engine.connect() as connection:
            result = list_speakers(connection)
    except SQLAlchemyError as exc:
        logger.exception("Personenliste nicht lesbar")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Die Datenbank ist nicht erreichbar.",
            headers={ERROR_CODE_HEADER: "unavailable"},
        ) from exc
    response.headers["Cache-Control"] = CACHE_CONTROL
    return result
