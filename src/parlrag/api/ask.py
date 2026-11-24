"""`POST /ask`: Frage → Antwort mit Quellen (Task 5.1; plan.md, Abschnitt 8).

Dieselbe `AskPipeline` wie `parlrag ask` und die Evals. Sie entsteht beim ersten Aufruf und wird
wiederverwendet; das Embedding-Modell lädt dadurch erst dann, `/health` hängt nicht davon ab.

Pro Anfrage eine Logzeile mit Usage, ohne den Wortlaut der Frage (Datenschutz bei einer
öffentlichen Demo): Länge, erkannte Sprache und aktive Filter genügen zur Diagnose.

In der Demo (Task 6.3a) prüfen Kostendeckel und Rate-Limit jede Anfrage vor der Pipeline
(`parlrag.api.limits`); sind sie ausgeschaltet, ändert sich nichts.

Jeder Fehler trägt zusätzlich einen maschinenlesbaren Code im Header `X-Error-Code` (Spec 002,
Task 7.5): Die Web-UI übersetzt daraus die Meldung, `detail` bleibt für andere Clients deutsch.
"""

import logging
import time
import uuid
from collections.abc import Callable
from functools import lru_cache
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import SQLAlchemyError

from parlrag.api.limits import (
    CostGuard,
    DemoLimits,
    LimitExceeded,
    PostgresUsageStore,
    RateLimiter,
    client_ip,
)
from parlrag.api.schemas import AskRequest, AskResponse, to_response
from parlrag.config import Settings
from parlrag.db.session import get_engine
from parlrag.generation.pipeline import AskPipeline, build_pipeline
from parlrag.llm import LLMConfigError, LLMError, LLMOutputError, LLMRefusalError
from parlrag.retrieval.fulltext import detect_query_language

logger = logging.getLogger("parlrag.api")
router = APIRouter()

REQUEST_ID_HEADER = "X-Request-ID"
ERROR_CODE_HEADER = "X-Error-Code"

# Fehlercodes für `X-Error-Code` (Plan 002, Abschnitt 6).
RATE_LIMIT = "rate_limit"
DAILY_BUDGET = "daily_budget"
LLM_UNAVAILABLE = "llm_unavailable"
UNAVAILABLE = "unavailable"
MODEL_REFUSED = "model_refused"
MODEL_OUTPUT = "model_output"
LIMIT_CODES = {"rate": RATE_LIMIT, "budget": DAILY_BUDGET}


@lru_cache(maxsize=1)
def get_pipeline() -> AskPipeline:
    """Einmal pro Prozess; ein Konfigurationsfehler wird nicht gespeichert (nächster Versuch)."""
    return build_pipeline()


def pipeline_provider() -> Callable[[], AskPipeline]:
    """Dependency: liefert die Fabrik, damit Konfigurationsfehler im Endpunkt geloggt werden
    (in Tests ersetzbar)."""
    return get_pipeline


@lru_cache(maxsize=1)
def get_limits() -> DemoLimits:
    """Grenzen der Demo aus der Konfiguration; ohne Werte ausgeschaltet (keine Datenbank nötig)."""
    settings = Settings()
    cost = (
        CostGuard(PostgresUsageStore(get_engine()), settings.demo_monthly_budget_usd)
        if settings.demo_monthly_budget_usd > 0
        else None
    )
    rate = RateLimiter(settings.rate_limit_per_hour) if settings.rate_limit_per_hour > 0 else None
    return DemoLimits(cost=cost, rate=rate, trust_proxy_headers=settings.trust_proxy_headers)


def limits_provider() -> DemoLimits:
    """Dependency (in Tests ersetzbar)."""
    return get_limits()


def _error_status(error: LLMError) -> tuple[int, str, str]:
    """HTTP-Status, Meldung (`detail`) und Fehlercode für einen Fehler des LLM."""
    if isinstance(error, LLMConfigError):
        return status.HTTP_503_SERVICE_UNAVAILABLE, f"LLM nicht verfügbar: {error}", LLM_UNAVAILABLE
    if isinstance(error, LLMRefusalError):
        return (
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Das Modell hat die Anfrage abgelehnt.",
            MODEL_REFUSED,
        )
    if isinstance(error, LLMOutputError):
        return (
            status.HTTP_502_BAD_GATEWAY,
            "Das Modell lieferte keine gültige Antwort.",
            MODEL_OUTPUT,
        )
    return (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        f"LLM vorübergehend nicht verfügbar: {error}",
        LLM_UNAVAILABLE,
    )


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
    http_request: Request,
    provide: Annotated[Callable[[], AskPipeline], Depends(pipeline_provider)],
    limits: Annotated[DemoLimits, Depends(limits_provider)],
) -> AskResponse:
    """Antwort mit nummerierten Quellen; reichen die Quellen nicht, ein klarer Hinweis."""
    request_id = uuid.uuid4().hex[:12]
    start = time.perf_counter()
    if limits.active:
        _admit(limits, http_request, request, request_id)
    try:
        result = provide().ask(request.question, request.filters, detect=request.detect)
    except LLMError as exc:
        http_status, message, code = _error_status(exc)
        latency_ms = (time.perf_counter() - start) * 1000
        _log(
            request_id,
            request,
            http_status,
            error=type(exc).__name__,
            latency_ms=f"{latency_ms:.0f}",
        )
        raise HTTPException(
            status_code=http_status,
            detail=message,
            headers={REQUEST_ID_HEADER: request_id, ERROR_CODE_HEADER: code},
        ) from exc

    latency_ms = (time.perf_counter() - start) * 1000
    body = to_response(result, latency_ms)
    usage = body.usage
    if limits.active:
        try:
            limits.record(usage.cost_usd)
        except SQLAlchemyError:
            logger.exception("api_usage konnte nicht gespeichert werden")
    _log(
        request_id,
        request,
        status.HTTP_200_OK,
        insufficient=body.insufficient_context,
        reason=body.insufficient_reason or "-",
        detected=",".join(body.filters.detected) or "-",
        retried=",".join(body.retried_without) or "-",
        candidates=len(body.speaker_candidates),
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


def _admit(limits: DemoLimits, http_request: Request, request: AskRequest, request_id: str) -> None:
    """Grenzen der Demo prüfen; bei Überschreitung 429 mit `Retry-After`."""
    ip = client_ip(
        http_request.headers.get("x-forwarded-for"),
        http_request.client.host if http_request.client else None,
        limits.trust_proxy_headers,
    )
    try:
        limits.admit(ip)
    except LimitExceeded as exc:
        _log(request_id, request, status.HTTP_429_TOO_MANY_REQUESTS, limit=exc.kind)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=exc.message,
            headers={
                REQUEST_ID_HEADER: request_id,
                ERROR_CODE_HEADER: LIMIT_CODES[exc.kind],
                "Retry-After": str(exc.retry_after),
            },
        ) from exc
    except SQLAlchemyError as exc:  # Ohne Zähler keine Kostenkontrolle: lieber ablehnen.
        logger.exception("api_usage nicht lesbar")
        _log(request_id, request, status.HTTP_503_SERVICE_UNAVAILABLE, limit="store")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Die Demo ist vorübergehend nicht verfügbar.",
            headers={REQUEST_ID_HEADER: request_id, ERROR_CODE_HEADER: UNAVAILABLE},
        ) from exc
