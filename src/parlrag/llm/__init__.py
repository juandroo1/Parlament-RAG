"""LLM: Interface und zwei Backends mit Tokens, Latenz und Kosten (Tasks 4.1 und 4.2a).

- `api`: Anthropic-API mit API-Key (Standard; Container, API, Demo).
- `claude-code`: eigenes Claude-Abo über die lokal installierte Claude-Code-CLI (AK-6.3).
"""

import shutil

import anthropic

from parlrag.config import Effort, Settings
from parlrag.llm.anthropic_client import DEFAULT_TIMEOUT_SECONDS, AnthropicLLM
from parlrag.llm.base import (
    LLMClient,
    LLMConfigError,
    LLMError,
    LLMOutputError,
    LLMRefusalError,
    LLMResult,
    Usage,
    sum_usage,
)
from parlrag.llm.claude_code_client import ClaudeCodeLLM

__all__ = [
    "AnthropicLLM",
    "ClaudeCodeLLM",
    "LLMClient",
    "LLMConfigError",
    "LLMError",
    "LLMOutputError",
    "LLMRefusalError",
    "LLMResult",
    "Usage",
    "get_llm",
    "sum_usage",
]


def get_llm(
    settings: Settings, *, model: str | None = None, effort: Effort | None = None
) -> LLMClient:
    """Claude gemäss `LLM_BACKEND`, `ANTHROPIC_MODEL` und `ANTHROPIC_EFFORT`.

    `model` und `effort` überschreiben die Einstellungen, z. B. für den Judge der Evals.
    """
    model = model or settings.anthropic_model
    effort = effort or settings.anthropic_effort
    if settings.llm_backend == "claude-code":
        executable = shutil.which("claude")
        if executable is None:
            raise LLMConfigError(
                "Claude Code CLI (`claude`) nicht gefunden. LLM_BACKEND=claude-code läuft nur "
                "lokal mit installiertem Claude Code; sonst LLM_BACKEND=api mit API-Key."
            )
        return ClaudeCodeLLM(model, effort, executable=executable)
    # Eine leere Zeile `ANTHROPIC_API_KEY=` aus .env.example ergibt einen leeren String.
    api_key = (
        settings.anthropic_api_key.get_secret_value().strip() if settings.anthropic_api_key else ""
    )
    if not api_key:
        raise LLMConfigError(
            "ANTHROPIC_API_KEY fehlt. Den Key in .env eintragen (Vorlage: .env.example)."
        )
    client = anthropic.Anthropic(api_key=api_key, timeout=DEFAULT_TIMEOUT_SECONDS)
    return AnthropicLLM(client, model, effort)
