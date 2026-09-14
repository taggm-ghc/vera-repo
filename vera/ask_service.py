"""OpenAI request handling for /ask: the completion call, token-usage
extraction, and cost calculation. OpenAI SDK exceptions intentionally
propagate to the routing layer, where main.py translates provider failures
into HTTP responses — this module has no knowledge of HTTP.
"""
from dataclasses import dataclass
from functools import lru_cache

from openai import OpenAI

from vera.pricing.config import PricingRecord


@dataclass(frozen=True)
class AskResult:
    answer: str
    tokens_used: int
    cost_usd: float


@lru_cache(maxsize=1)
def _get_client() -> OpenAI:
    """Construct the OpenAI client on first use, not at module import time."""
    return OpenAI()


def answer_question(question: str, model: str, pricing: PricingRecord) -> AskResult:
    completion = _get_client().chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": question}],
    )

    usage = completion.usage
    input_cost = (usage.prompt_tokens / 1_000_000) * pricing.input
    output_cost = (usage.completion_tokens / 1_000_000) * pricing.output

    return AskResult(
        answer=completion.choices[0].message.content,
        tokens_used=usage.total_tokens,
        cost_usd=round(input_cost + output_cost, 6),
    )
