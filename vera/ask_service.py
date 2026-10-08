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
    sources: tuple = ()  # item #79: numbered sources the answer was grounded in (empty when ungrounded)
    claim_check: dict | None = None  # item #79: per-claim check summary (grounded path only)


@lru_cache(maxsize=1)
def _get_client() -> OpenAI:
    """Construct the OpenAI client on first use, not at module import time."""
    return OpenAI()


def answer_question(question: str, model: str, pricing: PricingRecord, client: OpenAI | None = None,
                    extra_body: dict | None = None) -> AskResult:
    """client/extra_body are set only by the /ask provider chain (item #77); every other caller gets the
    default OpenAI client, so the evaluation paths are unchanged."""
    return complete([{"role": "user", "content": question}], model, pricing, client=client, extra_body=extra_body)


def complete(messages: list[dict], model: str, pricing: PricingRecord, client: OpenAI | None = None,
             extra_body: dict | None = None) -> AskResult:
    """One chat completion with token and cost accounting (shared by the bare and grounded /ask paths)."""
    completion = (client or _get_client()).chat.completions.create(
        model=model,
        messages=messages,
        **({"extra_body": extra_body} if extra_body else {}),
    )

    usage = completion.usage
    input_cost = (usage.prompt_tokens / 1_000_000) * pricing.input
    output_cost = (usage.completion_tokens / 1_000_000) * pricing.output

    return AskResult(
        answer=completion.choices[0].message.content,
        tokens_used=usage.total_tokens,
        cost_usd=round(input_cost + output_cost, 6),
    )


def answer_in_scope(question: str, model: str, pricing: PricingRecord, client: OpenAI | None = None,
                    extra_body: dict | None = None, grounding=None) -> AskResult:
    """The /ask entry point (item #72 W1): the scope router runs first; a declined question never reaches the
    answering model and gets the fixed decline template. answer_question stays the bare model call (the trace
    harness's baseline shape)."""
    from vera.scope_router import decline_text, route

    from vera.scope_router import default_chat

    def chat(messages, model_, l2):
        return default_chat(messages, model_, l2, client=client, extra_body=extra_body)

    decision = route(question, model, pricing, chat=chat if (client or extra_body) else None)
    if not decision.accepted:
        return AskResult(answer=decline_text(), tokens_used=decision.tokens_used, cost_usd=decision.cost_usd)
    chained = {k: v for k, v in (("client", client), ("extra_body", extra_body)) if v}  # only from the #77 chain
    if grounding is not None:  # item #79: grounding = (sources_fn, cfg); sources_fn caches one search per request
        from vera.grounded_ask import fix_citations, messages_for

        sources_fn, cfg = grounding
        sources = sources_fn()
        if not sources:  # never answer from memory on the grounded path
            return AskResult(answer=cfg["no_sources_text"], tokens_used=decision.tokens_used,
                             cost_usd=decision.cost_usd)
        from vera.grounded_ask import count_valid_citations

        result = complete(messages_for(question, sources), model, pricing, **chained)
        text, _ = fix_citations(result.answer or "", len(sources), cfg["removed_citation_note"])
        tokens = result.tokens_used + decision.tokens_used
        cost = round(result.cost_usd + decision.cost_usd, 6)
        if count_valid_citations(text, len(sources)) == 0:  # R1 criterion: no valid citation -> no answer
            return AskResult(answer=cfg["insufficient_text"], tokens_used=tokens, cost_usd=cost,
                             sources=tuple(sources), claim_check={"checked": 0, "outcome": "no_valid_citations"})
        cc = cfg.get("claim_check") or {}
        if cc.get("enabled"):  # R1 criterion: each cited claim checked against the cited text; fail closed
            from vera.claim_check import check_answer

            checked, summary = check_answer(text, sources, cc)
            if checked is None:
                fallback = cc["unavailable_text"] if summary["outcome"] == "checker_unavailable" else cfg["insufficient_text"]
                return AskResult(answer=fallback, tokens_used=tokens, cost_usd=cost, sources=tuple(sources),
                                 claim_check=summary)
            return AskResult(answer=checked, tokens_used=tokens, cost_usd=cost, sources=tuple(sources),
                             claim_check=summary)
        return AskResult(answer=text, tokens_used=tokens, cost_usd=cost, sources=tuple(sources))
    result = answer_question(question, model, pricing, **chained)
    return AskResult(answer=result.answer, tokens_used=result.tokens_used + decision.tokens_used,
                     cost_usd=round(result.cost_usd + decision.cost_usd, 6))
