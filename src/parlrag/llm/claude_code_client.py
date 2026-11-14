"""Claude-Abo als LLM-Backend über die Claude-Code-CLI (Task 4.2a, AK-6.3).

Nur für die lokale, eigene Nutzung: Erlaubt ist, sich mit dem eigenen Abo in der unveränderten
Claude-Code-App anzumelden; andere Personen über ein Abo zu bedienen ist nicht erlaubt
(plan.md, Entscheidungsprotokoll). Container, API und Demo nutzen `LLM_BACKEND=api`.

Ein Aufruf ist `claude -p` mit strukturierter Ausgabe (`--json-schema`), eigenem System-Prompt
aus einer Datei, ohne Werkzeuge und ohne CLAUDE.md, MCP, Hooks oder Plugins (`--safe-mode`).
Die Frage geht über stdin, weil lange Prompts unter Windows die Länge einer Kommandozeile
überschreiten. `--bare` ginge nicht: Es liest die Abo-Anmeldung nie.
"""

import json
import os
import subprocess
import tempfile
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

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

DEFAULT_TIMEOUT_SECONDS = 300.0
STDERR_EXCERPT = 300

# Variablen, die den Aufruf vom Abo weglenken (API-Key geht im Skript-Modus immer vor), den
# Effort überschreiben oder ihn an eine aufrufende Claude-Code-Sitzung binden würden.
STRIPPED_PREFIXES = ("ANTHROPIC_", "CLAUDE_CODE_SESSION", "CLAUDE_CODE_MESSAGING")
STRIPPED_VARIABLES = frozenset(
    {
        "CLAUDE_CODE_EFFORT_LEVEL",
        "CLAUDE_CODE_OAUTH_TOKEN",
        "CLAUDE_CODE_USE_BEDROCK",
        "CLAUDE_CODE_USE_VERTEX",
        "CLAUDE_CODE_USE_FOUNDRY",
        "CLAUDE_CODE_CHILD_SESSION",
        "CLAUDE_CODE_ENTRYPOINT",
        "CLAUDE_CODE_EXECPATH",
        "CLAUDE_CODE_SSE_PORT",
        "CLAUDECODE",
        "CLAUDE_EFFORT",
        "CLAUDE_PID",
    }
)

Runner = Callable[..., subprocess.CompletedProcess[str]]


def subprocess_env(environ: Mapping[str, str]) -> dict[str, str]:
    """Umgebung für die CLI ohne Variablen, die das Abo umgehen oder die Sitzung verfälschen."""
    return {
        key: value
        for key, value in environ.items()
        if key not in STRIPPED_VARIABLES and not key.startswith(STRIPPED_PREFIXES)
    }


class ClaudeCodeLLM:
    def __init__(
        self,
        model: str,
        effort: Effort,
        *,
        executable: str,
        runner: Runner = subprocess.run,
        clock: Callable[[], float] = time.perf_counter,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._model = model
        self.effort = effort
        self.executable = executable
        self.runner = runner
        self.clock = clock
        self.timeout = timeout
        self._login_checked = False

    @property
    def model(self) -> str:
        return self._model

    def check_login(self) -> None:
        """Prüft mit `claude auth status`, dass Claude Code angemeldet ist (gibt nichts aus)."""
        process = self._run([self.executable, "auth", "status"], stdin=None, cwd=None)
        try:
            status = json.loads(process.stdout)
        except json.JSONDecodeError:
            status = {}
        if not status.get("loggedIn"):
            raise LLMConfigError(
                "Claude Code ist nicht angemeldet. `claude` starten und mit dem Claude-Abo "
                "anmelden, oder LLM_BACKEND=api mit API-Key verwenden."
            )
        self._login_checked = True

    def generate[T: BaseModel](self, *, system: str, user: str, schema: type[T]) -> LLMResult[T]:
        if not self._login_checked:
            self.check_login()
        with tempfile.TemporaryDirectory(prefix="parlrag-claude-") as workdir:
            system_file = Path(workdir) / "system.md"
            system_file.write_text(system, encoding="utf-8")
            args = [
                self.executable,
                "-p",
                "--output-format",
                "json",
                "--model",
                self._model,
                "--effort",
                self.effort,
                "--tools",
                "",
                "--safe-mode",
                "--no-session-persistence",
                "--strict-mcp-config",
                "--system-prompt-file",
                str(system_file),
                "--json-schema",
                json.dumps(schema.model_json_schema()),
            ]
            start = self.clock()
            process = self._run(args, stdin=user, cwd=workdir)
            latency_ms = (self.clock() - start) * 1000

        data = _parse(process)
        usage = _usage(data, latency_ms, self._model)
        fallback_used = usage.model != self._model
        log_call(usage, data.get("stop_reason"), fallback_used)
        _raise_for_error(data, usage)
        if data.get("stop_reason") == "refusal":
            raise LLMRefusalError("Anfrage abgelehnt.", usage)
        output = data.get("structured_output")
        if output is None:
            raise LLMOutputError("Keine strukturierte Ausgabe erhalten.", usage)
        try:
            parsed = schema.model_validate(output)
        except ValidationError as exc:
            raise LLMOutputError(
                f"Ausgabe passt nicht zum Schema {schema.__name__}.", usage
            ) from exc
        return LLMResult(output=parsed, usage=usage, fallback_used=fallback_used)

    def _run(
        self, args: list[str], *, stdin: str | None, cwd: str | None
    ) -> subprocess.CompletedProcess[str]:
        try:
            return self.runner(
                args,
                input=stdin,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=subprocess_env(os.environ),
                cwd=cwd,
                timeout=self.timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise LLMConfigError(
                "Claude Code CLI (`claude`) nicht gefunden. Das Abo-Backend läuft nur lokal; "
                "im Container LLM_BACKEND=api mit API-Key verwenden."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise LLMError(f"Claude Code hat nach {self.timeout:.0f} s nicht geantwortet.") from exc


def _parse(process: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    try:
        data = json.loads(process.stdout)
    except json.JSONDecodeError:
        data = None
    if not isinstance(data, dict):
        excerpt = (process.stderr or process.stdout or "").strip()[:STDERR_EXCERPT]
        raise LLMError(f"Claude Code beendet mit Code {process.returncode}: {excerpt}")
    return data


def _usage(data: dict[str, Any], latency_ms: float, requested_model: str) -> Usage:
    """Tokens summiert über alle Modelle in `modelUsage`; Kosten = Schätzung von Claude Code."""
    per_model: dict[str, dict[str, Any]] = data.get("modelUsage") or {}

    def total(field: str) -> int:
        return sum(int(entry.get(field) or 0) for entry in per_model.values())

    if requested_model in per_model or not per_model:
        model = requested_model
    else:  # z. B. ein Fallback-Modell von Claude Code
        model = max(per_model, key=lambda name: int(per_model[name].get("outputTokens") or 0))
    cost = data.get("total_cost_usd")
    return Usage(
        model=model,
        input_tokens=total("inputTokens"),
        output_tokens=total("outputTokens"),
        cache_creation_input_tokens=total("cacheCreationInputTokens"),
        cache_read_input_tokens=total("cacheReadInputTokens"),
        latency_ms=latency_ms,
        cost_usd=float(cost) if cost is not None else None,
        backend="claude-code",
    )


def _raise_for_error(data: dict[str, Any], usage: Usage) -> None:
    subtype = data.get("subtype")
    if not data.get("is_error") and subtype == "success":
        return
    status = data.get("api_error_status")
    if status in (401, 403):
        raise LLMConfigError(
            "Claude-Abo-Anmeldung abgelehnt. `claude` starten und neu anmelden.", usage
        )
    if status == 429:
        detail = str(data.get("result") or "").strip()[:STDERR_EXCERPT]
        raise LLMError(
            "Limit des Claude-Abos erreicht (429"
            + (f": {detail}" if detail else "")
            + "). Später erneut versuchen oder LLM_BACKEND=api mit API-Key verwenden.",
            usage,
        )
    if subtype == "error_max_structured_output_retries":
        raise LLMOutputError("Keine gültige strukturierte Ausgabe nach mehreren Versuchen.", usage)
    detail = str(data.get("result") or "")[:STDERR_EXCERPT]
    raise LLMError(f"Claude Code meldet einen Fehler ({subtype}, Status {status}): {detail}", usage)
