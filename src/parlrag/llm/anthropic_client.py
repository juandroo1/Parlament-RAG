"""Anthropic-Implementierung des LLM-Interfaces (plan.md, Abschnitte 2 und 7).

- Strukturierte Ausgabe über `messages.parse` mit einem Pydantic-Schema.
- Claude Opus 5.5 denkt immer (adaptiv); gesteuert wird nur über den Effort.
- Serverseitiger Fallback bei Ablehnungen (`fallbacks: "default"`): Lehnt das Modell ab,
  antwortet im selben Aufruf ein anderes Modell. Kosten werden pro beteiligtem Modell gerechnet.
  Nur für Modelle, die ihn unterstützen (z. B. nicht Haiku 5.5).
- Das SDK wiederholt 408/409/429/5xx und Verbindungsfehler selbst.
"""

import time
from collections.abc import Callable
from typing import Any

import anthropic
from pydantic import BaseModel, ValidationError

from parlrag.config import Effort
from parlrag.llm.base import (
    LLMConfigError,
    LLMError,
    LLMOutputError,
    LLMRefusalError,
    LLMResult,
    Usage,
    log_call,
)
from parlrag.llm.pricing import cost_usd

FALLBACK_BETA = "server-side-fallback-2026-07-01"
# Modelle mit serverseitigem Fallback; bei anderen (z. B. Haiku 5.5) wäre der Parameter ein Fehler.
FALLBACK_MODELS = frozenset(
    {
        "claude-opus-5-5",
        "claude-sonnet-5-5",
        "claude-opus-5",
        "claude-fable-5-2",
        "claude-fable-5-1",
    }
)
DEFAULT_MAX_TOKENS = 16_000
DEFAULT_TIMEOUT_SECONDS = 120.0


class AnthropicLLM:
    def __init__(
        self,
        client: anthropic.Anthropic,
        model: str,
        effort: Effort,
        *,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        fallback: bool | None = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self.client = client
        self._model = model
        self.effort = effort
        self.max_tokens = max_tokens
        # Ohne Angabe: Fallback, wenn das Modell ihn unterstützt.
        self.fallback = model in FALLBACK_MODELS if fallback is None else fallback
        self.clock = clock

    @property
    def model(self) -> str:
        return self._model

    def generate[T: BaseModel](self, *, system: str, user: str, schema: type[T]) -> LLMResult[T]:
        request: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "output_format": schema,
            "output_config": {"effort": self.effort},
        }
        if self.fallback:
            request |= {"betas": [FALLBACK_BETA], "fallbacks": "default"}

        start = self.clock()
        try:
            response = self.client.beta.messages.parse(**request)
        except anthropic.AuthenticationError as exc:
            raise LLMConfigError(
                "Anthropic API lehnt den API-Key ab (ANTHROPIC_API_KEY prüfen)."
            ) from exc
        except anthropic.APIStatusError as exc:
            raise LLMError(f"Anthropic API Fehler {exc.status_code}: {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError("Keine Verbindung zur Anthropic API.") from exc
        except ValidationError as exc:
            raise LLMOutputError(f"Ausgabe passt nicht zum Schema {schema.__name__}.") from exc
        latency_ms = (self.clock() - start) * 1000

        usage = _usage(response, latency_ms)
        fallback_used = response.model != self._model
        log_call(usage, response.stop_reason, fallback_used)

        if response.stop_reason == "refusal":
            details = response.stop_details
            category = getattr(details, "category", None) if details else None
            raise LLMRefusalError(
                f"Anfrage abgelehnt (Kategorie: {category or 'unbekannt'}).", usage, category
            )
        if response.stop_reason == "max_tokens":
            raise LLMOutputError(f"Ausgabe nach {self.max_tokens} Tokens abgeschnitten.", usage)
        if response.parsed_output is None:
            raise LLMOutputError("Keine strukturierte Ausgabe erhalten.", usage)
        return LLMResult(output=response.parsed_output, usage=usage, fallback_used=fallback_used)


def _usage(response: Any, latency_ms: float) -> Usage:
    """Tokens aus der Gesamtsumme; Kosten pro Iteration (abgelehntes Modell und Fallback)."""
    total = response.usage
    tokens = {
        "input_tokens": total.input_tokens,
        "output_tokens": total.output_tokens,
        "cache_creation_input_tokens": total.cache_creation_input_tokens or 0,
        "cache_read_input_tokens": total.cache_read_input_tokens or 0,
    }
    iterations = getattr(total, "iterations", None) or []
    costs = (
        [
            cost_usd(
                getattr(it, "model", None) or response.model,
                it.input_tokens,
                it.output_tokens,
                it.cache_creation_input_tokens or 0,
                it.cache_read_input_tokens or 0,
            )
            for it in iterations
        ]
        if iterations
        else [cost_usd(response.model, **tokens)]
    )
    cost = None if any(c is None for c in costs) else sum(c for c in costs if c is not None)
    return Usage(model=response.model, latency_ms=latency_ms, cost_usd=cost, **tokens)
