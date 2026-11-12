"""FastAPI-Anwendung. Start: `uvicorn parlrag.api.main:app`."""

from typing import Annotated

from fastapi import Depends, FastAPI, Response, status
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from parlrag import __version__
from parlrag.db.session import get_engine

app = FastAPI(title="Frag das Parlament", version=__version__)


@app.get("/health")
def health(response: Response, engine: Annotated[Engine, Depends(get_engine)]) -> dict[str, str]:
    """Healthcheck für Docker: 200, wenn die App läuft und die Datenbank antwortet, sonst 503."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "error", "database": "unreachable"}
    return {"status": "ok", "database": "ok"}
