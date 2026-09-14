import logging
import os
from enum import Enum

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from openai import AuthenticationError, OpenAIError, RateLimitError
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from vera.ask_service import answer_question
from vera.auth import (
    OPENAI_KEY_ERROR_DETAIL,
    classify_openai_api_key,
    classify_vera_api_key,
    verify_api_key,
)
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


class AskResponse(BaseModel):
    answer: str
    model: str
    tokens_used: int
    cost_usd: float


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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse, dependencies=[Depends(verify_api_key)])
def ask(req: AskRequest):
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
        result = answer_question(req.question, MODEL, CURRENT_PRICING)
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

    return AskResponse(
        answer=result.answer,
        model=MODEL,
        tokens_used=result.tokens_used,
        cost_usd=result.cost_usd,
    )
