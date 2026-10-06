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


def answer_in_scope(question: str, model: str, pricing: PricingRecord) -> AskResult:
    """The /ask entry point (item #72 W1): the scope router runs first; a declined question never reaches the
    answering model and gets the fixed decline template. answer_question stays the bare model call (the trace
    harness's baseline shape)."""
    from vera.scope_router import decline_text, route

    decision = route(question, model, pricing)
    if not decision.accepted:
        return AskResult(answer=decline_text(), tokens_used=decision.tokens_used, cost_usd=decision.cost_usd)
    result = answer_question(question, model, pricing)
    return AskResult(answer=result.answer, tokens_used=result.tokens_used + decision.tokens_used,
                     cost_usd=round(result.cost_usd + decision.cost_usd, 6))
