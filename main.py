import logging
import os
from enum import Enum

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from openai import AuthenticationError, OpenAIError, RateLimitError
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from vera.corpus_admission import admit as admit_to_corpus, llm_call_for, store_from_env
from vera.corpus_description import CorpusDescriber, generate_with_chain, load_cfg as load_corpus_description_cfg
from vera.grounded_ask import load_corpus_cfg, load_grounding, public_sources, retrieve_all
from vera.memory_store import load_memory_block, memory_from_env
from vera.inference_chain import answer_via_chain, load_chain
from vera.auth import (
    OPENAI_KEY_ERROR_DETAIL,
    classify_openai_api_key,
    classify_vera_api_key,
    verify_api_key,
)
from vera.public_mode import enforce_caps, record_request_cost
from vera.pricing.config import latest_pricing_for, load_model_pricing, load_model_selection

load_dotenv()  # read OPENAI_API_KEY (and anything else) from .env

logger = logging.getLogger("vera")
logging.basicConfig(level=logging.INFO)

app = FastAPI()


# --- Model selection and pricing config -------------------------------------
# Schema, loaders, and the append-only writer live in vera/pricing/config.py,
# shared with scripts/append_model_pricing.py and
# scripts/refresh_openai_pricing.py — main.py just coordinates: load config,
# pick the active record, hand it to the service layer. See the Resource
# invariant in docs/vera-design.md: config is version-controlled JSON, not a
# database, because Render's filesystem is ephemeral and would not preserve a
# runtime database file across a redeploy.

_model_selection = load_model_selection()
_model_pricing = load_model_pricing()

MODEL = _model_selection.selected_model if _model_selection else "gpt-4o-mini"
CURRENT_PRICING = latest_pricing_for(MODEL, _model_pricing)
ASK_CHAIN = load_chain(MODEL, CURRENT_PRICING)  # item #77: free-tier providers first, OpenAI last
GROUNDING = load_grounding()  # item #79: live scholarly retrieval for /ask (None = ungrounded)
CORPUS = load_corpus_cfg()  # item #79 phase C: corpus admission settings (None = disabled)
_DESC_CFG = load_corpus_description_cfg()  # item #83
MEMORY_BLOCK = load_memory_block()  # item #84
CORPUS_DESCRIBER = CorpusDescriber(_DESC_CFG) if _DESC_CFG else None

if CURRENT_PRICING is None:
    logger.warning(
        "No usable pricing record for model %s at startup — /ask will reject requests "
        "until config/model-pricing.json has a record for this model", MODEL,
    )


# --- API key startup checks --------------------------------------------------
# Classification policy lives in vera/auth.py. main.py coordinates startup
# checks so configuration problems surface before the affected request path.

for _status, _var in (
    (classify_openai_api_key(os.getenv("OPENAI_API_KEY")), "OPENAI_API_KEY"),
    (classify_vera_api_key(os.getenv("VERA_API_KEY")), "VERA_API_KEY"),
):
    if _status != "ok":
        logger.warning("%s looks %s at startup — requests that need it will be rejected until it's fixed in .env", _var, _status)


class APIModel(BaseModel):
    """Shared base: unknown fields 422, they are never silently dropped."""

    model_config = ConfigDict(extra="forbid")


class DemoMode(str, Enum):
    normal = "normal"
    force_bad = "force_bad"


class AskRequest(APIModel):
    question: str = Field(..., max_length=4000)
    mode: DemoMode = DemoMode.normal


class AskSource(BaseModel):
    n: int
    title: str
    url: str
    published: str | None = None
    source_type: str | None = None
    provider: str | None = None  # item #79: per-citation provenance (R1 criterion)
    identifier: str | None = None
    retrieved_at: str | None = None
    licence_decision: str | None = None


class AskResponse(BaseModel):
    answer: str
    model: str
    tokens_used: int
    cost_usd: float
    sources: list[AskSource] = []  # item #79: what the answer was grounded in (no abstracts)
    traced_sources: list[AskSource] = []  # item #79: originals traced from links but with no free abstract (not used)
    recalled: list[dict] = []  # item #84: earlier checked findings relevant to this question (never the question)
    memory_written: int = 0  # item #84: findings saved after the claim check and the write gate
    claim_check: dict | None = None  # item #79: how many cited claims were checked, kept, marked or removed


class SyntheticFault(str, Enum):
    """Deliberately invalid AskResponse payloads, one violation each, used by the
    force_bad demo mode to prove the real response schema rejects malformed output."""

    non_numeric_tokens = "non_numeric_tokens"
    non_numeric_cost = "non_numeric_cost"
    null_answer = "null_answer"


_SYNTHETIC_FAULT_BASE = {"answer": "placeholder", "model": MODEL, "tokens_used": 0, "cost_usd": 0.0}

SYNTHETIC_FAULT_PAYLOADS: dict[SyntheticFault, dict] = {
    SyntheticFault.non_numeric_tokens: {**_SYNTHETIC_FAULT_BASE, "tokens_used": "not-a-number"},
    SyntheticFault.non_numeric_cost: {**_SYNTHETIC_FAULT_BASE, "cost_usd": "not-a-float"},
    SyntheticFault.null_answer: {**_SYNTHETIC_FAULT_BASE, "answer": None},
}

# force_bad always injects this one fault; not selectable via AskRequest — see
# ask-guardrail-design-prv.md FMEA #9 on not expanding the public request contract casually.
FORCE_BAD_FAULT = SyntheticFault.non_numeric_tokens


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


class CorpusDescription(BaseModel):
    source_count: int | None = None
    corpus_updated_at: str | None = None
    summary: str | None = None
    topics: list[str] = []
    summary_source: str
    summary_generated_at: str | None = None
    summary_model: str | None = None


@app.get("/corpus-summary", response_model=CorpusDescription, dependencies=[Depends(verify_api_key)])
def corpus_summary():
    """Item #83: description of VERA's own corpus, regenerated only when it changes. Behind VERA_API_KEY like /ask
    (the UI calls it server-side); no titles, URLs or abstracts in the response."""
    if CORPUS_DESCRIBER is None:
        return CorpusDescription(summary_source="disabled")
    try:
        return CorpusDescription(**CORPUS_DESCRIBER.current(generate_with_chain(ASK_CHAIN)))
    except Exception as exc:  # noqa: BLE001  (DB unreachable etc.: a generic state, never the error text)
        logger.warning("corpus description unavailable (%s)", type(exc).__name__)
        return CorpusDescription(summary_source="unavailable")


@app.get("/health")
def health():
    return {"status": "ok"}


def _after_response(admit_args, memory, result, question: str) -> None:
    """Background: corpus admission first, then memory writes (never raises, never affects the response)."""
    try:
        if admit_args:
            admit_to_corpus(*admit_args)
        if memory is not None and result.claims:
            memory.write_claims(result.claims, list(result.sources), question)
    except Exception as exc:  # noqa: BLE001
        logger.warning("post-response task failed (%s)", type(exc).__name__)


@app.post("/ask", response_model=AskResponse, dependencies=[Depends(verify_api_key), Depends(enforce_caps)])  # W2 caps (public mode)
def ask(req: AskRequest, request: Request, background_tasks: BackgroundTasks):
    if req.mode is DemoMode.force_bad:
        # Guardrail demo: inject one identified synthetic fault, rejected by real
        # schema validation. No OpenAI call is made — the demo is free and deterministic.
        fault = FORCE_BAD_FAULT
        try:
            AskResponse(**SYNTHETIC_FAULT_PAYLOADS[fault])
        except ValidationError as exc:
            logger.info(
                "force_bad invoked: synthetic fault '%s' rejected by schema validation: %s",
                fault.value, exc.errors(),
            )
            raise HTTPException(
                status_code=500,
                detail="Guardrail demo: synthetic malformed output was rejected by schema validation.",
            ) from exc

    key_status = classify_openai_api_key(os.getenv("OPENAI_API_KEY"))
    if key_status != "ok":
        logger.error("Rejected /ask: OPENAI_API_KEY is %s", key_status)
        raise HTTPException(status_code=500, detail=OPENAI_KEY_ERROR_DETAIL[key_status])

    if CURRENT_PRICING is None:
        logger.error("Rejected /ask: no pricing record for model %s", MODEL)
        raise HTTPException(
            status_code=500,
            detail=f"Server misconfigured: no pricing record for model '{MODEL}' in config/model-pricing.json",
        )

    try:
        # scope router first (item #72 W1); free providers first, OpenAI last (item #77)
        grounding, cache = None, {}
        if GROUNDING is not None:

            def sources_fn():  # one search per request, reused if the provider chain falls through
                if "s" not in cache:
                    cache["s"], cache["unused"] = retrieve_all(req.question, GROUNDING)
                return cache["s"]

            grounding = (sources_fn, GROUNDING)
        result, answered_by = answer_via_chain(req.question, ASK_CHAIN, grounding)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=401,
            detail=(
                "OpenAI rejected the API key. Check that OPENAI_API_KEY in .env is current "
                "and belongs to an active account."
            ),
        ) from exc
    except RateLimitError as exc:
        quota_markers = {"insufficient_quota", "credit_balance_exhausted"}
        if getattr(exc, "code", None) in quota_markers or getattr(exc, "type", None) in quota_markers:
            raise HTTPException(
                status_code=402,
                detail=(
                    "The OpenAI account for this API key has no remaining credit, so the "
                    "request was not answered. Add a payment method or credits at "
                    "https://platform.openai.com/settings/organization/billing/ and retry."
                ),
            ) from exc
        raise HTTPException(
            status_code=429,
            detail="OpenAI rate limit hit (too many requests). Wait a few seconds and retry.",
        ) from exc
    except OpenAIError as exc:
        logger.error("OpenAI request failed: %s", exc)
        raise HTTPException(status_code=502, detail="OpenAI request failed. Please try again.") from exc

    record_request_cost(request, result.cost_usd)
    store = store_from_env(CORPUS) if result.sources else None
    memory = None
    recalled, memory_written = [], 0  # memory_written stays 0: writes are asynchronous (background, after admission)
    if result.accepted:  # item #84: recall and write only for in-scope questions; errors never fail /ask
        try:
            memory = memory_from_env(MEMORY_BLOCK)
            if memory is not None:
                recalled = memory.recall(req.question)  # recall is synchronous
        except Exception as exc:  # noqa: BLE001
            logger.warning("memory failed (%s)", type(exc).__name__)
    admit_args = (req.question, list(result.sources), llm_call_for(ASK_CHAIN[0]), CORPUS, store) \
        if store is not None and ASK_CHAIN else None
    if admit_args or (memory is not None and result.claims):
        # item #79 phase C + item #84: after the response, never delaying it. Memory writes run AFTER corpus
        # admission so first-time sources are already in the corpus when their claims are saved.
        background_tasks.add_task(_after_response, admit_args, memory, result, req.question)
    return AskResponse(
        recalled=recalled,
        memory_written=memory_written,
        answer=result.answer,
        model=answered_by,
        tokens_used=result.tokens_used,
        cost_usd=result.cost_usd,
        sources=public_sources(list(result.sources)),
        claim_check=result.claim_check,
        traced_sources=[{"n": i, **{k: t.get(k) for k in ("title", "url", "published")}, "source_type": "traced"}
                        for i, t in enumerate(cache.get("unused") or [], 1)],
    )
