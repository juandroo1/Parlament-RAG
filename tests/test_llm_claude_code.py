"""Claude-Abo als LLM-Backend über die Claude-Code-CLI (Task 4.2a, AK-6.3).

Ohne echten `claude`-Prozess: Ein Fake-Runner liefert die JSON-Ausgabe, wie sie die CLI
(Version 2.1.323) bei `claude -p --output-format json --json-schema …` zurückgibt.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, SecretStr

from parlrag.config import Settings
from parlrag.llm import (
    ClaudeCodeLLM,
    LLMConfigError,
    LLMError,
    LLMOutputError,
    LLMRefusalError,
    get_llm,
)
from parlrag.llm.claude_code_client import subprocess_env

MODEL = "claude-haiku-5-5"
AUTH_OK = {"loggedIn": True, "authMethod": "claude.ai", "email": "person@example.com"}


class Answer(BaseModel):
    answer: str
    citations: list[int]


def _result(**changes: Any) -> dict[str, Any]:
    """Gekürzte echte Ausgabe eines erfolgreichen Aufrufs (Testaufruf vom 2026-11-14)."""
    base: dict[str, Any] = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "num_turns": 2,
        "stop_reason": "tool_use",
        "api_error_status": None,
        "result": '{"answer":"Le Conseil fédéral demande le rejet [1].","citations":[1]}',
        "structured_output": {
            "answer": "Le Conseil fédéral demande le rejet [1].",
            "citations": [1],
        },
        "total_cost_usd": 0.00517,
        "usage": {"input_tokens": 2, "output_tokens": 194},
        "modelUsage": {
            MODEL: {
                "inputTokens": 2,
                "outputTokens": 194,
                "cacheReadInputTokens": 0,
                "cacheCreationInputTokens": 25364,
                "costUSD": 0.00517,
            }
        },
    }
    return base | changes


class FakeRunner:
    def __init__(
        self,
        result: dict[str, Any] | str | BaseException,
        auth: dict[str, Any] | None = None,
        returncode: int = 0,
        stderr: str = "",
    ) -> None:
        self.result = result
        self.auth = AUTH_OK if auth is None else auth
        self.returncode = returncode
        self.stderr = stderr
        self.calls: list[dict[str, Any]] = []
        self.system_prompts: list[str] = []

    def __call__(self, args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append({"args": args, **kwargs})
        if args[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(args, 0, stdout=json.dumps(self.auth), stderr="")
        system_file = Path(args[args.index("--system-prompt-file") + 1])
        self.system_prompts.append(system_file.read_text(encoding="utf-8"))
        if isinstance(self.result, BaseException):
            raise self.result
        stdout = self.result if isinstance(self.result, str) else json.dumps(self.result)
        return subprocess.CompletedProcess(args, self.returncode, stdout=stdout, stderr=self.stderr)

    @property
    def prompt_calls(self) -> list[dict[str, Any]]:
        return [call for call in self.calls if "-p" in call["args"]]


def _llm(runner: FakeRunner) -> ClaudeCodeLLM:
    ticks = iter([10.0, 12.5] * 10)
    return ClaudeCodeLLM(
        MODEL, "low", executable="claude", runner=runner, clock=lambda: next(ticks)
    )


def _generate(llm: ClaudeCodeLLM) -> Any:
    return llm.generate(system="Antworte nur aus den Quellen.", user="Frage?", schema=Answer)


def test_cli_arguments_and_input() -> None:
    runner = FakeRunner(_result())
    _generate(_llm(runner))

    (call,) = runner.prompt_calls
    args = call["args"]
    assert args[:2] == ["claude", "-p"]
    for flag, value in [
        ("--output-format", "json"),
        ("--model", MODEL),
        ("--effort", "low"),
        ("--tools", ""),
    ]:
        assert args[args.index(flag) + 1] == value
    for flag in ("--safe-mode", "--no-session-persistence", "--strict-mcp-config"):
        assert flag in args
    assert "--bare" not in args  # --bare liest die Abo-Anmeldung nie
    assert "--max-turns" not in args  # strukturierte Ausgabe braucht zwei Durchgänge
    assert json.loads(args[args.index("--json-schema") + 1]) == Answer.model_json_schema()
    assert runner.system_prompts == ["Antworte nur aus den Quellen."]
    system_file = Path(args[args.index("--system-prompt-file") + 1])
    assert system_file.parent == Path(call["cwd"])  # leeres temporäres Verzeichnis
    assert not system_file.exists()  # nach dem Aufruf aufgeräumt
    assert call["input"] == "Frage?"  # über stdin, nicht als Argument
    assert call["timeout"] == 300.0 and call["check"] is False


def test_environment_is_cleaned(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_EFFORT_LEVEL", "CLAUDECODE"):
        monkeypatch.setenv(name, "x")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "C:/config")
    runner = FakeRunner(_result())
    _generate(_llm(runner))

    env = runner.prompt_calls[0]["env"]
    assert "ANTHROPIC_API_KEY" not in env  # ginge im Skript-Modus immer vor dem Abo
    assert "CLAUDE_CODE_EFFORT_LEVEL" not in env and "CLAUDECODE" not in env
    assert env["CLAUDE_CONFIG_DIR"] == "C:/config"  # dort liegt die Anmeldung


def test_subprocess_env() -> None:
    environ = {
        "PATH": "/bin",
        "ANTHROPIC_AUTH_TOKEN": "t",
        "ANTHROPIC_BASE_URL": "u",
        "CLAUDE_CODE_OAUTH_TOKEN": "o",
        "CLAUDE_CODE_USE_BEDROCK": "1",
        "CLAUDE_CODE_SESSION_ID": "s",
        "CLAUDE_CODE_MESSAGING_TOKEN": "m",
        "CLAUDE_CODE_GIT_BASH_PATH": "C:/git/bash.exe",
        "CLAUDE_EFFORT": "high",
    }
    assert subprocess_env(environ) == {
        "PATH": "/bin",
        "CLAUDE_CODE_GIT_BASH_PATH": "C:/git/bash.exe",
    }


def test_result_and_usage(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="parlrag.llm"):
        result = _generate(_llm(FakeRunner(_result())))

    assert result.output == Answer(answer="Le Conseil fédéral demande le rejet [1].", citations=[1])
    assert not result.fallback_used
    usage = result.usage
    assert (usage.backend, usage.model) == ("claude-code", MODEL)
    assert (usage.input_tokens, usage.output_tokens) == (2, 194)
    assert usage.cache_creation_input_tokens == 25364 and usage.cache_read_input_tokens == 0
    assert usage.cost_usd == pytest.approx(0.00517)  # Schätzung von Claude Code
    assert usage.latency_ms == pytest.approx(2500.0)  # inklusive Start der CLI
    assert "llm_call backend=claude-code model=claude-haiku-5-5" in caplog.text


def test_tokens_are_summed_and_fallback_model_reported() -> None:
    model_usage = {
        "claude-sonnet-5-5": {"inputTokens": 10, "outputTokens": 300, "costUSD": 0.004},
        "claude-haiku-5-5-extra": {"inputTokens": 5, "outputTokens": 20},
    }
    result = _generate(_llm(FakeRunner(_result(modelUsage=model_usage, total_cost_usd=None))))

    assert result.usage.model == "claude-sonnet-5-5" and result.fallback_used
    assert (result.usage.input_tokens, result.usage.output_tokens) == (15, 320)
    assert result.usage.cost_usd is None


def test_login_is_checked_once() -> None:
    runner = FakeRunner(_result())
    llm = _llm(runner)
    _generate(llm)
    _generate(llm)

    auth_calls = [call for call in runner.calls if call["args"][1:3] == ["auth", "status"]]
    assert len(auth_calls) == 1 and len(runner.prompt_calls) == 2


def test_not_logged_in_is_a_config_error() -> None:
    runner = FakeRunner(_result(), auth={"loggedIn": False, "email": "person@example.com"})
    with pytest.raises(LLMConfigError, match="nicht angemeldet") as info:
        _generate(_llm(runner))
    assert "person@example.com" not in str(info.value)  # keine E-Mail in Meldungen
    assert runner.prompt_calls == []


@pytest.mark.parametrize(
    ("changes", "expected", "message"),
    [
        (
            {"is_error": True, "subtype": "error_during_execution", "api_error_status": 429},
            LLMError,
            "Limit des Claude-Abos",
        ),
        (
            {"is_error": True, "subtype": "error_during_execution", "api_error_status": 401},
            LLMConfigError,
            "neu anmelden",
        ),
        (
            {"is_error": True, "subtype": "error_max_structured_output_retries"},
            LLMOutputError,
            "strukturierte Ausgabe",
        ),
        (
            {"is_error": True, "subtype": "error_during_execution", "result": "boom"},
            LLMError,
            r"error_during_execution, Status None\): boom",
        ),
        ({"stop_reason": "refusal", "structured_output": None}, LLMRefusalError, "abgelehnt"),
        ({"structured_output": None}, LLMOutputError, "Keine strukturierte Ausgabe"),
        ({"structured_output": {"answer": 1}}, LLMOutputError, "Schema Answer"),
    ],
)
def test_errors_in_result(changes: dict[str, Any], expected: type[LLMError], message: str) -> None:
    with pytest.raises(expected, match=message) as info:
        _generate(_llm(FakeRunner(_result(**changes))))
    assert type(info.value) is expected
    assert info.value.usage is not None and info.value.usage.backend == "claude-code"


def test_unparsable_output_reports_exit_code_and_stderr() -> None:
    runner = FakeRunner("kein json", returncode=1, stderr="Fehler: etwas ging schief\n")
    with pytest.raises(LLMError, match="Code 1: Fehler: etwas ging schief"):
        _generate(_llm(runner))


@pytest.mark.parametrize(
    ("error", "expected", "message"),
    [
        (FileNotFoundError("claude"), LLMConfigError, "nicht gefunden"),
        (subprocess.TimeoutExpired("claude", 300), LLMError, "300 s"),
    ],
)
def test_process_errors(error: BaseException, expected: type[LLMError], message: str) -> None:
    with pytest.raises(expected, match=message):
        _generate(_llm(FakeRunner(error)))


def _settings(**values: Any) -> Settings:
    return Settings(_env_file=None, postgres_password=SecretStr("x"), **values)


def test_get_llm_claude_code_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda name: "C:/bin/claude.exe")
    llm = get_llm(
        _settings(llm_backend="claude-code", anthropic_model=MODEL, anthropic_effort="low")
    )

    assert isinstance(llm, ClaudeCodeLLM)
    assert (llm.model, llm.effort, llm.executable) == (MODEL, "low", "C:/bin/claude.exe")


def test_get_llm_claude_code_needs_the_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda name: None)
    with pytest.raises(LLMConfigError, match="nicht gefunden"):
        get_llm(_settings(llm_backend="claude-code"))


def test_api_backend_is_default() -> None:
    assert _settings().llm_backend == "api"
    with pytest.raises(LLMConfigError, match="ANTHROPIC_API_KEY"):
        get_llm(_settings())  # ohne Key: weiterhin klare Meldung


def test_get_llm_model_and_effort_can_be_overridden(monkeypatch: pytest.MonkeyPatch) -> None:
    """Der Judge der Evals nutzt dasselbe Backend mit eigenem Modell (JUDGE_MODEL)."""
    monkeypatch.setattr("shutil.which", lambda name: "C:/bin/claude.exe")
    settings = _settings(llm_backend="claude-code", anthropic_model=MODEL, anthropic_effort="low")
    judge = get_llm(settings, model="claude-sonnet-5-5", effort="medium")

    assert isinstance(judge, ClaudeCodeLLM)
    assert (judge.model, judge.effort) == ("claude-sonnet-5-5", "medium")
    assert _settings().judge_model == "claude-sonnet-5-5" and _settings().judge_effort == "medium"


def test_subscription_limit_message_includes_reset_time() -> None:
    limit = _result(
        is_error=True,
        subtype="success",
        api_error_status=429,
        result="You've hit your 5-hour limit · resets 4:30pm (Europe/Zurich)",
    )
    with pytest.raises(LLMError, match=r"429: You've hit your 5-hour limit · resets 4:30pm"):
        _generate(_llm(FakeRunner(limit)))
