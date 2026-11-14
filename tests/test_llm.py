"""LLM-Interface und Anthropic-Implementierung (Task 4.1), mit Fake-SDK-Client ohne Netzwerk."""

import logging
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx2
import pytest
from pydantic import BaseModel, SecretStr

from parlrag.config import Settings
from parlrag.llm import (
    AnthropicLLM,
    LLMConfigError,
    LLMError,
    LLMOutputError,
    LLMRefusalError,
    get_llm,
)
from parlrag.llm.anthropic_client import FALLBACK_BETA
from parlrag.llm.pricing import cost_usd

MODEL = "claude-opus-5-5"


class Answer(BaseModel):
    answer: str
    citations: list[int]


def _usage(
    input_tokens: int = 1000,
    output_tokens: int = 500,
    cache_write: int | None = 200,
    cache_read: int | None = 3000,
    iterations: list[Any] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_input_tokens=cache_write,
        cache_read_input_tokens=cache_read,
        iterations=iterations,
    )


def _response(
    parsed: BaseModel | None = None,
    stop_reason: str = "end_turn",
    model: str = MODEL,
    usage: SimpleNamespace | None = None,
    stop_details: Any = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        parsed_output=parsed,
        stop_reason=stop_reason,
        stop_details=stop_details,
        model=model,
        usage=usage or _usage(),
    )


class FakeMessages:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def parse(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


def _llm(result: Any, **options: Any) -> tuple[AnthropicLLM, FakeMessages]:
    messages = FakeMessages(result)
    client = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    ticks = iter([1.0, 1.25])
    llm = AnthropicLLM(
        client,  # type: ignore[arg-type]
        MODEL,
        "high",
        clock=lambda: next(ticks),
        **options,
    )
    return llm, messages


def _generate(llm: AnthropicLLM) -> Any:
    return llm.generate(system="Antworte nur aus den Quellen.", user="Frage?", schema=Answer)


def test_request_parameters() -> None:
    llm, messages = _llm(_response(Answer(answer="Ja [1].", citations=[1])))
    _generate(llm)

    (call,) = messages.calls
    assert call["model"] == MODEL
    assert call["max_tokens"] == 16_000
    assert call["system"] == "Antworte nur aus den Quellen."
    assert call["messages"] == [{"role": "user", "content": "Frage?"}]
    assert call["output_format"] is Answer
    assert call["output_config"] == {"effort": "high"}
    assert "thinking" not in call  # Opus 5.5 denkt immer; gesteuert wird über den Effort
    assert call["betas"] == [FALLBACK_BETA] and call["fallbacks"] == "default"


def test_fallback_can_be_disabled() -> None:
    llm, messages = _llm(_response(Answer(answer="x", citations=[])), fallback=False)
    _generate(llm)
    assert "fallbacks" not in messages.calls[0] and "betas" not in messages.calls[0]


def test_result_carries_output_tokens_latency_and_cost() -> None:
    llm, _ = _llm(_response(Answer(answer="Ja [1].", citations=[1])))
    result = _generate(llm)

    assert result.output == Answer(answer="Ja [1].", citations=[1])
    assert not result.fallback_used
    usage = result.usage
    assert (usage.model, usage.input_tokens, usage.output_tokens) == (MODEL, 1000, 500)
    assert (usage.cache_creation_input_tokens, usage.cache_read_input_tokens) == (200, 3000)
    assert usage.latency_ms == pytest.approx(250.0)
    expected = (1000 * 4.00 + 500 * 20.00 + 200 * 5.00 + 3000 * 0.20) / 1_000_000
    assert usage.cost_usd == pytest.approx(expected)


def test_missing_cache_fields_count_as_zero() -> None:
    llm, _ = _llm(
        _response(Answer(answer="x", citations=[]), usage=_usage(cache_write=None, cache_read=None))
    )
    usage = _generate(llm).usage
    assert usage.cache_creation_input_tokens == 0 and usage.cache_read_input_tokens == 0
    assert usage.cost_usd == pytest.approx((1000 * 4.00 + 500 * 20.00) / 1_000_000)


def test_fallback_cost_is_summed_per_model() -> None:
    iterations = [
        SimpleNamespace(
            type="message",
            model=MODEL,
            input_tokens=1000,
            output_tokens=50,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        ),
        SimpleNamespace(
            type="fallback_message",
            model="claude-opus-4-8",
            input_tokens=1000,
            output_tokens=400,
            cache_creation_input_tokens=None,
            cache_read_input_tokens=None,
        ),
    ]
    response = _response(
        Answer(answer="x", citations=[]),
        model="claude-opus-4-8",
        usage=_usage(2000, 450, 0, 0, iterations),
    )
    result = _generate(_llm(response)[0])

    assert result.fallback_used
    assert result.usage.model == "claude-opus-4-8"
    expected = (1000 * 4.00 + 50 * 20.00 + 1000 * 5.00 + 400 * 25.00) / 1_000_000
    assert result.usage.cost_usd == pytest.approx(expected)


def test_unknown_model_has_no_cost(caplog: pytest.LogCaptureFixture) -> None:
    response = _response(Answer(answer="x", citations=[]), model="claude-unknown-9")
    with caplog.at_level(logging.WARNING):
        result = _generate(_llm(response)[0])

    assert result.usage.cost_usd is None
    assert "Kein Preis für Modell claude-unknown-9" in caplog.text


def test_call_is_logged_with_usage(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="parlrag.llm"):
        _generate(_llm(_response(Answer(answer="x", citations=[])))[0])

    line = caplog.records[-1].getMessage()
    assert line.startswith(
        "llm_call backend=api model=claude-opus-5-5 stop_reason=end_turn fallback=False"
    )
    assert "input_tokens=1000 output_tokens=500" in line
    assert "latency_ms=250" in line and "cost_usd=0.015600" in line


def test_refusal_raises_with_category_and_usage() -> None:
    details = SimpleNamespace(type="refusal", category="cyber", explanation="…")
    llm, _ = _llm(_response(None, stop_reason="refusal", stop_details=details))

    with pytest.raises(LLMRefusalError, match="cyber") as info:
        _generate(llm)
    assert info.value.category == "cyber"
    assert info.value.usage is not None and info.value.usage.cost_usd is not None


def test_truncated_output_raises() -> None:
    llm, _ = _llm(_response(None, stop_reason="max_tokens"))
    with pytest.raises(LLMOutputError, match="abgeschnitten") as info:
        _generate(llm)
    assert info.value.usage is not None


def test_missing_parsed_output_raises() -> None:
    with pytest.raises(LLMOutputError, match="Keine strukturierte Ausgabe"):
        _generate(_llm(_response(None))[0])


def test_invalid_output_raises_output_error() -> None:
    try:
        Answer.model_validate({"answer": 1})
    except Exception as exc:
        validation_error = exc
    with pytest.raises(LLMOutputError, match="Answer"):
        _generate(_llm(validation_error)[0])


_REQUEST = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


@pytest.mark.parametrize(
    ("error", "expected", "message"),
    [
        (
            anthropic.AuthenticationError(
                "invalid x-api-key", response=httpx2.Response(401, request=_REQUEST), body=None
            ),
            LLMConfigError,
            "API-Key",
        ),
        (
            anthropic.RateLimitError(
                "rate limited", response=httpx2.Response(429, request=_REQUEST), body=None
            ),
            LLMError,
            "429",
        ),
        (anthropic.APIConnectionError(request=_REQUEST), LLMError, "Keine Verbindung"),
    ],
)
def test_sdk_errors_are_translated(
    error: Exception, expected: type[LLMError], message: str
) -> None:
    with pytest.raises(expected, match=message) as info:
        _generate(_llm(error)[0])
    assert type(info.value) is expected


@pytest.mark.parametrize("key", [None, SecretStr(""), SecretStr("  ")])
def test_get_llm_requires_api_key(key: SecretStr | None) -> None:
    """Auch die leere Zeile `ANTHROPIC_API_KEY=` aus .env.example gilt als fehlend."""
    settings = Settings(_env_file=None, postgres_password=SecretStr("x"), anthropic_api_key=key)
    with pytest.raises(LLMConfigError, match="ANTHROPIC_API_KEY"):
        get_llm(settings)


def test_get_llm_uses_settings() -> None:
    settings = Settings(
        _env_file=None,
        postgres_password=SecretStr("x"),
        anthropic_api_key=SecretStr("sk-ant-test"),
        anthropic_model="claude-sonnet-5-5",
        anthropic_effort="medium",
    )
    llm = get_llm(settings)

    assert isinstance(llm, AnthropicLLM)
    assert (llm.model, llm.effort) == ("claude-sonnet-5-5", "medium")
    assert llm.client.api_key == "sk-ant-test"
    assert llm.client.timeout == 120.0


def test_pricing() -> None:
    assert cost_usd(MODEL, 1_000_000, 0) == pytest.approx(4.00)
    assert cost_usd(MODEL, 0, 1_000_000) == pytest.approx(20.00)
    assert cost_usd("claude-sonnet-5-5", 0, 0, 1_000_000, 1_000_000) == pytest.approx(2.60)
    assert cost_usd("claude-unknown-9", 1, 1) is None


def test_fallback_only_for_models_that_support_it() -> None:
    """Haiku 5.5 hat keinen serverseitigen Fallback; der Parameter liesse den Aufruf scheitern."""
    messages = FakeMessages(_response(Answer(answer="x", citations=[]), model="claude-haiku-5-5"))
    client = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    haiku = AnthropicLLM(client, "claude-haiku-5-5", "low")  # type: ignore[arg-type]
    sonnet = AnthropicLLM(client, "claude-sonnet-5-5", "high")  # type: ignore[arg-type]

    assert not haiku.fallback and sonnet.fallback
    result = haiku.generate(system="s", user="u", schema=Answer)
    assert "fallbacks" not in messages.calls[0]
    assert not result.fallback_used


def test_haiku_pricing_has_long_prompt_tier() -> None:
    short = cost_usd("claude-haiku-5-5", 100_000, 1_000_000)
    assert short == pytest.approx(0.01 + 0.50)
    long = cost_usd("claude-haiku-5-5", 60_000, 1_000_000, 0, 50_000)  # Prompt 110'000 Tokens
    assert long == pytest.approx((60_000 * 0.50 + 1_000_000 * 2.50 + 50_000 * 0.05) / 1_000_000)
