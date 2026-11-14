"""LLM: Interface und Anthropic-Implementierung mit Tokens, Latenz und Kosten (Task 4.1)."""

import anthropic

from parlrag.config import Settings
from parlrag.llm.anthropic_client import DEFAULT_TIMEOUT_SECONDS, AnthropicLLM
from parlrag.llm.base import (
    LLMClient,
    LLMConfigError,
    LLMError,
    LLMOutputError,
    LLMRefusalError,
    LLMResult,
    Usage,
)

__all__ = [
    "AnthropicLLM",
    "LLMClient",
    "LLMConfigError",
    "LLMError",
    "LLMOutputError",
    "LLMRefusalError",
    "LLMResult",
    "Usage",
    "get_llm",
]


def get_llm(settings: Settings) -> LLMClient:
    """Claude gemäss `ANTHROPIC_MODEL` und `ANTHROPIC_EFFORT`; der API-Key ist Pflicht."""
    # Eine leere Zeile `ANTHROPIC_API_KEY=` aus .env.example ergibt einen leeren String.
    api_key = (
        settings.anthropic_api_key.get_secret_value().strip() if settings.anthropic_api_key else ""
    )
    if not api_key:
        raise LLMConfigError(
            "ANTHROPIC_API_KEY fehlt. Den Key in .env eintragen (Vorlage: .env.example)."
        )
    client = anthropic.Anthropic(api_key=api_key, timeout=DEFAULT_TIMEOUT_SECONDS)
    return AnthropicLLM(client, settings.anthropic_model, settings.anthropic_effort)
