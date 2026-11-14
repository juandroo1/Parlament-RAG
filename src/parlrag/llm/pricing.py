"""Geschätzte Kosten pro Aufruf (spec.md, Abschnitt 6: Kosten pro Frage).

Preise in USD pro Million Tokens, Anthropic-API, Stand 2026-11. Thinking-Tokens werden als
Output abgerechnet und sind in `output_tokens` enthalten. Cache schreiben gilt für die
Standard-TTL von 5 Minuten.
"""

from dataclasses import dataclass

PRICES_AS_OF = "2026-11"


@dataclass(frozen=True)
class ModelPrice:
    input: float
    output: float
    cache_write: float
    cache_read: float


PRICES: dict[str, ModelPrice] = {
    "claude-opus-5-5": ModelPrice(input=4.00, output=20.00, cache_write=5.00, cache_read=0.20),
    "claude-sonnet-5-5": ModelPrice(input=2.00, output=10.00, cache_write=2.50, cache_read=0.10),
    # Mögliche Ziele des serverseitigen Fallbacks bei Ablehnungen.
    "claude-opus-5": ModelPrice(input=5.00, output=25.00, cache_write=6.25, cache_read=0.50),
    "claude-opus-4-8": ModelPrice(input=5.00, output=25.00, cache_write=6.25, cache_read=0.50),
}


def cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_input_tokens: int = 0,
    cache_read_input_tokens: int = 0,
) -> float | None:
    """Kosten in USD; None bei unbekanntem Modell (lieber keine Zahl als eine falsche)."""
    price = PRICES.get(model)
    if price is None:
        return None
    return (
        input_tokens * price.input
        + output_tokens * price.output
        + cache_creation_input_tokens * price.cache_write
        + cache_read_input_tokens * price.cache_read
    ) / 1_000_000
