"""`POST /ask`: Frage → Antwort mit Quellen (Task 5.1; plan.md, Abschnitt 8).

Dieselbe `AskPipeline` wie `parlrag ask` und die Evals. Sie entsteht beim ersten Aufruf und wird
wiederverwendet; das Embedding-Modell lädt dadurch erst dann, `/health` hängt nicht davon ab.

Pro Anfrage eine Logzeile mit Usage, ohne den Wortlaut der Frage (Datenschutz bei einer
öffentlichen Demo): Länge, erkannte Sprache und aktive Filter genügen zur Diagnose.
"""

import logging
import time
import uuid
from collections.abc import Callable
from functools import lru_cache
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status

from parlrag.api.schemas import AskRequest, AskResponse, to_response
from parlrag.generation.pipeline import AskPipeline, build_pipeline
from parlrag.llm import LLMConfigError, LLMError, LLMOutputError, LLMRefusalError
from parlrag.retrieval.fulltext import detect_query_language

logger = logging.getLogger("parlrag.api")
router = APIRouter()

REQUEST_ID_HEADER = "X-Request-ID"


@lru_cache(maxsize=1)
def get_pipeline() -> AskPipeline:
    """Einmal pro Prozess; ein Konfigurationsfehler wird nicht gespeichert (nächster Versuch)."""
    return build_pipeline()


def pipeline_provider() -> Callable[[], AskPipeline]:
    """Dependency: liefert die Fabrik, damit Konfigurationsfehler im Endpunkt geloggt werden
    (in Tests ersetzbar)."""
    return get_pipeline


def _error_status(error: LLMError) -> tuple[int, str]:
    if isinstance(error, LLMConfigError):
        return status.HTTP_503_SERVICE_UNAVAILABLE, f"LLM nicht verfügbar: {error}"
    if isinstance(error, LLMRefusalError):
        return status.HTTP_422_UNPROCESSABLE_CONTENT, "Das Modell hat die Anfrage abgelehnt."
    if isinstance(error, LLMOutputError):
        return status.HTTP_502_BAD_GATEWAY, "Das Modell lieferte keine gültige Antwort."
    return status.HTTP_503_SERVICE_UNAVAILABLE, f"LLM vorübergehend nicht verfügbar: {error}"


def _log(request_id: str, request: AskRequest, http_status: int, **fields: Any) -> None:
    filters = request.filters.model_dump(exclude_none=True, mode="json") if request.filters else {}
    parts = {
        "request_id": request_id,
        "status": http_status,
        "question_chars": len(request.question),
        "language": detect_query_language(request.question) or "-",
        "filters": ",".join(f"{key}={value}" for key, value in filters.items()) or "-",
        **fields,
    }
    logger.info("ask_request " + " ".join(f"{key}={value}" for key, value in parts.items()))


@router.post("/ask", response_model=AskResponse)
def ask(
    request: AskRequest,
    response: Response,
    provide: Annotated[Callable[[], AskPipeline], Depends(pipeline_provider)],
) -> AskResponse:
    """Antwort mit nummerierten Quellen; reichen die Quellen nicht, ein klarer Hinweis."""
    request_id = uuid.uuid4().hex[:12]
    start = time.perf_counter()
    try:
        result = provide().ask(request.question, request.filters)
    except LLMError as exc:
        http_status, message = _error_status(exc)
        latency_ms = (time.perf_counter() - start) * 1000
        _log(
            request_id,
            request,
            http_status,
            error=type(exc).__name__,
            latency_ms=f"{latency_ms:.0f}",
        )
        raise HTTPException(
            status_code=http_status, detail=message, headers={REQUEST_ID_HEADER: request_id}
        ) from exc

    latency_ms = (time.perf_counter() - start) * 1000
    body = to_response(result, latency_ms)
    usage = body.usage
    _log(
        request_id,
        request,
        status.HTTP_200_OK,
        insufficient=body.insufficient_context,
        reason=body.insufficient_reason or "-",
        sources=len(body.sources),
        model=usage.model or "-",
        backend=usage.backend or "-",
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cost_usd=f"{usage.cost_usd:.6f}" if usage.cost_usd is not None else "unbekannt",
        latency_ms=f"{latency_ms:.0f}",
    )
    response.headers[REQUEST_ID_HEADER] = request_id
    return body
