"""FastAPI-Anwendung. Start: `uvicorn parlrag.api.main:app`."""

from fastapi import FastAPI

from parlrag import __version__

app = FastAPI(title="Frag das Parlament", version=__version__)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness-Check für den Docker-Healthcheck. Der Datenbank-Check folgt in Task 0.4."""
    return {"status": "ok"}
