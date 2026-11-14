"""LLM-Interface (plan.md, Abschnitt 7): strukturierte Ausgabe, Tokens, Latenz und Kosten.

Die Logik ruft das LLM nur über `LLMClient` auf (CLAUDE.md), nie direkt über ein SDK.
"""

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel


@dataclass(frozen=True)
class Usage:
    """Verbrauch eines Aufrufs; `cost_usd` ist None, wenn ein Preis unbekannt ist."""

    model: str
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float | None = None


@dataclass(frozen=True)
class LLMResult[T: BaseModel]:
    """Validierte Ausgabe und Verbrauch; `model` in `usage` ist das Modell, das geantwortet hat."""

    output: T
    usage: Usage
    fallback_used: bool = False


class LLMError(RuntimeError):
    """Aufruf fehlgeschlagen; `usage` ist gesetzt, wenn trotzdem Kosten angefallen sind."""

    def __init__(self, message: str, usage: Usage | None = None) -> None:
        super().__init__(message)
        self.usage = usage


class LLMConfigError(LLMError):
    """Fehlende oder ungültige Konfiguration, z. B. kein API-Key."""


class LLMRefusalError(LLMError):
    """Das Modell (und ein allfälliges Fallback-Modell) hat die Anfrage abgelehnt."""

    def __init__(self, message: str, usage: Usage | None = None, category: str | None = None):
        super().__init__(message, usage)
        self.category = category


class LLMOutputError(LLMError):
    """Die Ausgabe ist abgeschnitten oder passt nicht zum Schema."""


class LLMClient(Protocol):
    """Ein LLM mit strukturierter Ausgabe nach einem Pydantic-Schema."""

    @property
    def model(self) -> str: ...

    def generate[T: BaseModel](self, *, system: str, user: str, schema: type[T]) -> LLMResult[T]:
        """Ein Aufruf mit System-Prompt und einer Nutzernachricht; Ausgabe nach `schema`."""
        ...
