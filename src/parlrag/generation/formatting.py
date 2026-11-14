"""Ausgabe von `parlrag ask`: Antwort, Quellen (AK-2.1, AK-2.2), Verbrauch und Zeiten."""

import json
from typing import Any

from parlrag.generation.pipeline import AskResult
from parlrag.llm import Usage
from parlrag.retrieval.formatting import hit_metadata, snippet

REASONS = {
    "no_hits": "Grund: Die Suche fand keine Treffer.",
    "model": "Grund: Das Modell fand in den Quellen keine Antwort auf die Frage.",
}


def reason_line(result: AskResult) -> str | None:
    answer = result.answer
    if answer.insufficient_reason == "low_similarity" and answer.best_similarity is not None:
        return (
            f"Grund: beste Similarity {answer.best_similarity:.2f} unter der Schwelle "
            f"{result.min_similarity:.2f} (kein LLM-Aufruf)."
        )
    return REASONS.get(answer.insufficient_reason or "")


def _cost(usage: Usage) -> str:
    if usage.cost_usd is None:
        return "Kosten unbekannt"
    if usage.backend == "claude-code":
        return f"≈ {usage.cost_usd:.4f} USD geschätzt, im Claude-Abo enthalten"
    return f"{usage.cost_usd:.4f} USD"


def _number(value: int) -> str:
    return f"{value:,}".replace(",", "'")


def usage_line(usage: Usage | None, attempts: int) -> str:
    if usage is None:
        return "Kein LLM-Aufruf."
    # Input inklusive Cache: Claude Code legt den ganzen Prompt im Cache ab, sonst stünde hier ~2.
    cached = usage.cache_creation_input_tokens + usage.cache_read_input_tokens
    tokens = f"{_number(usage.input_tokens + cached)} Input-"
    if cached:
        tokens += f" (davon {_number(cached)} Cache)"
    line = (
        f"{usage.model} ({usage.backend}) · {tokens} und "
        f"{_number(usage.output_tokens)} Output-Tokens · {_cost(usage)}"
    )
    return line + (f" · {attempts} Versuche" if attempts > 1 else "")


def timing_line(result: AskResult, model_load_ms: float | None = None) -> str:
    line = (
        f"Suche {result.retrieval_ms:.0f} ms · LLM {result.generation_ms / 1000:.1f} s · "
        f"gesamt {result.total_ms / 1000:.1f} s"
    )
    if model_load_ms is not None:
        line += f" (Embedding-Modell vorher geladen in {model_load_ms / 1000:.1f} s)"
    return line


def format_answer(result: AskResult, model_load_ms: float | None = None) -> str:
    answer = result.answer
    active = result.filters.model_dump(exclude_none=True, mode="json")
    header = f"Frage «{result.question}»"
    if active:
        header += " · Filter " + ", ".join(f"{key}={value}" for key, value in active.items())
    lines = [header, "", answer.answer]
    if answer.insufficient_context:
        reason = reason_line(result)
        if reason:
            lines += ["", reason]
    else:
        lines += ["", "Quellen:"]
        for source in answer.sources:
            hit = source.hit
            lines += [
                f"[{source.number}] {hit_metadata(hit)}",
                "    " + snippet(hit.text),
                "    " + hit.url,
            ]
    lines += ["", usage_line(answer.usage, answer.attempts), timing_line(result, model_load_ms)]
    return "\n".join(lines)


def answer_payload(result: AskResult, model_load_ms: float | None = None) -> dict[str, Any]:
    """Strukturiert, nahe an der Antwort von `POST /ask` (plan.md, Abschnitt 8)."""
    answer = result.answer
    usage = answer.usage
    return {
        "question": result.question,
        "filters": result.filters.model_dump(exclude_none=True, mode="json"),
        "mode": result.mode,
        "answer": answer.answer,
        "insufficient_context": answer.insufficient_context,
        "insufficient_reason": answer.insufficient_reason,
        "best_similarity": answer.best_similarity,
        "min_similarity": result.min_similarity,
        "sources": [
            {
                "number": source.number,
                "source_key": source.hit.source_key,
                "source_type": source.hit.source_type,
                "language": source.hit.language,
                "title": source.hit.title,
                "speaker_name": source.hit.speaker_name,
                "speaker_function": source.hit.speaker_function,
                "parl_group": source.hit.parl_group,
                "canton": source.hit.canton,
                "council": source.hit.council,
                "date": source.hit.date.isoformat(),
                "business_numbers": list(source.hit.business_numbers),
                "section": source.hit.section,
                "text": source.hit.text,
                "url": source.hit.url,
            }
            for source in answer.sources
        ],
        "usage": None
        if usage is None
        else {
            "model": usage.model,
            "backend": usage.backend,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cache_creation_input_tokens": usage.cache_creation_input_tokens,
            "cache_read_input_tokens": usage.cache_read_input_tokens,
            "cost_usd": usage.cost_usd,
            "cost_estimated": usage.backend == "claude-code",
            "latency_ms": round(usage.latency_ms, 1),
        },
        "timings": {
            "retrieval_ms": round(result.retrieval_ms, 1),
            "generation_ms": round(result.generation_ms, 1),
            "total_ms": round(result.total_ms, 1),
            "model_load_ms": round(model_load_ms, 1) if model_load_ms is not None else None,
        },
        "attempts": answer.attempts,
        "prompt_version": answer.prompt_version,
    }


def answer_json(result: AskResult, model_load_ms: float | None = None) -> str:
    return json.dumps(answer_payload(result, model_load_ms), ensure_ascii=False, indent=2)
