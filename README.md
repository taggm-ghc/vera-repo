# VERA

## Verifiable Evidence-based Research Answers

**VERA is a provenance-grounded agentic context-engineering system that
discovers, critically evaluates, registers, and organizes evidence into
an auditable reasoning context to produce research responses measurably
superior to direct leading-LLM baselines.**

VERA is being developed as a capstone project for TAI Labs' Agentic AI
Engineering program.

## The Problem

Large language models can produce fluent research answers without making
the underlying evidence-selection process sufficiently inspectable.

A plausible answer is not necessarily a well-supported answer.
Conversely, an elaborate research process has limited value if its final
answer is no better than what a leading model can produce directly.

VERA therefore treats both **evidentiary defensibility** and **response
quality** as requirements.

The project examines a bounded question:

> Can deliberate, auditable evidence acquisition, critical evaluation,
> and context construction cause a frontier model to produce a
> materially better research response than it produces directly?

## What VERA Does

Given a bounded research question, VERA:

-   discovers and critically evaluates relevant evidence;
-   preserves evidence provenance;
-   constructs a deliberately selected research context;
-   produces a grounded research response; and
-   evaluates the resulting response against a direct leading-model
    baseline.

At a public architectural level:

``` text
Research Question
       |
       v
Evidence Discovery and Evaluation
       |
       v
Provenance-Grounded Context
       |
       v
Research Synthesis
       |
       v
Evaluation
       |
       v
Auditable Research Answer
```

The internal decision structures, representations, scoring methods,
orchestration mechanisms, and other implementation details used to
perform these functions are outside the scope of this public repository.

## Design Objectives

VERA is designed around four public objectives:

**Grounding.** Research claims should be supported by relevant evidence
rather than generated solely from model parameters.

**Provenance.** Consequential evidence should remain traceable to its
source.

**Auditability.** Evidence-selection and evaluation decisions should be
inspectable.

**Response quality.** Provenance and auditability are requirements, but
they do not compensate for an inferior final answer.

## Comparative Evaluation

VERA is evaluated against direct responses to the same bounded research
question from leading language models.

The central question is whether supplying a deliberately constructed,
critically evaluated evidence context produces a materially better
research response than direct model generation.

Evaluation considers the quality of the resulting answer as well as the
traceability of its supporting evidence.

## API

VERA is implemented as a Python service using FastAPI.

The application interface includes:

``` text
GET  /health
POST /ask
GET  /corpus-summary
```

`GET /health` provides a basic service health check (no key).

`POST /ask` is the primary research-question interface (key: `VERA_API_KEY`). Since 2026-10-07 (items #77 and
#79): the scope router runs first; an accepted question is searched live (arXiv, OpenAlex, DuckDuckGo links
followed to original papers); the answer is written only from the retrieved abstracts with [n] citations, each
cited claim is checked against the cited abstract, and unsupported sentences are removed. Request:
`{"question": "...", "mode": "normal"}`. Response:

``` text
answer          text with [n] citations (or a decline, no-sources or insufficient-evidence reply)
model           provider:model that answered (Groq first, OpenAI fallback)
tokens_used     integer
cost_usd        number (0 on the Groq free tier)
sources         [{n, title, url, published, source_type, provider, identifier, retrieved_at, licence_decision}]
traced_sources  originals found from links but without a free abstract (listed, not used)
claim_check     {checked, supported, partial, removed, checker, outcome}
```

`GET /corpus-summary` (key: `VERA_API_KEY`; item #83) describes VERA's own admitted sources: count, newest
source time, a model-written description and topics; no titles, URLs or abstracts.

The M2-M6 research pipeline under `vera/` (with Gate C, M5 verification and the M6 judge) remains a separate,
offline path; `/ask` reuses its search providers, Gate A and licence gate, not the whole pipeline.

## Model Choice

VERA currently uses OpenAI's `gpt-4.1-nano`. At this stage the deliverable
is a reliable, cost-observable `/ask` contract rather than answer quality
tuned across models, so the cheapest acceptable model is used rather than
a flagship one; this is revisited once response quality becomes a
load-bearing evaluation dimension.

Where the model name comes from today (read from code 2026-10-02): `vera/pipeline_llm.py` takes
the default from `config/model-selection.json` and falls back to a hardcoded `gpt-4.1-nano`;
`vera/gate_a.py` and `vera/m6/baseline_collection.py` hardcode `gpt-4.1-nano` themselves.

`/ask` only (2026-10-07, item #77): free providers first. `config/ask-provider-chain.json` lists Groq
`openai/gpt-oss-20b`, then `openai/gpt-oss-120b` (free tier, recorded at $0, `reasoning_effort` low); an entry
whose key is unset is skipped, and the selected OpenAI model is always the last resort. Any provider error
or an empty answer moves the request to the next entry; the response's `model` field names the one that
answered. Evaluation paths (TRACE capture, M6 baseline and judge, Gate A, pipeline) do not use the chain.
Because free answers cost $0, the daily cost cap only binds on OpenAI fallbacks; the request caps still
apply. The unused per-task file `.vera-provider-chain.json` was removed (its Groq model was retired).

Grounded `/ask` (2026-10-07, item #79). For each question the scope router accepts, `/ask` searches arXiv,
OpenAlex and DuckDuckGo once (`config/ask-provider-chain.json` `grounding`). Results with an abstract are
used directly. Link-only results (DuckDuckGo, news, portals, OpenAlex records without an abstract) are
followed to the original paper (`vera/source_resolver.py`): the page's citation DOI, arXiv, SSRN and linked
DOIs, one more hop through known scholarly hosts, then an OpenAlex title match (Jaccard >= 0.8) for portals
that refuse the fetch; abstracts come from OpenAlex, then Semantic Scholar. All counts, hops and time limits
are in the `resolve` block. The answer uses the grounded-v1 prompt (numbered abstracts, cite only), invalid
citation numbers are removed with a note, and the response lists `sources` (no abstracts) and
`traced_sources` (originals found without a free abstract, not used). With no usable source, `/ask` says so
and does not answer from memory.

Corpus growth (item #79 phase C). After the response, each source with an abstract goes through Gate A
(`vera/gate_a.py`, scored by the first `/ask` provider) and the licence gate (`vera/licence_gate.py`). Every
candidate is recorded with its decision; `fetch` decisions the licence gate allows are stored as corpus
sources (metadata and abstract only) under one fixed corpus question per process. The visitor's question is
never stored. Writes use the production write-only account `vera_pipeline_wo` via `VERA_DB_URL_WO` (unset =
disabled); every step is one INSERT ... RETURNING, so a source already in the corpus is counted as known.

The M6 judge must come from a different model family than the generator. Since goal #2 (2026-10-02,
offline, not yet run live) the judge is chosen at run time from the live list of Groq-served models
whose family is not OpenAI, using the pool, patterns and limits in `config/vera_eval_run.json`
(`vera/judge_select.py`, `vera/eval_config.py`). No model is a code default; the family is looked up by
model id and an unmapped model is refused. The choice is recorded per run and fixed within a run. The
family patterns are not yet checked against Groq's live list. No Anthropic key will be used (item A2
dropped 2026-10-02) and the Anthropic judge was removed from the code. Mistral is not supported.

## Running Locally

### Requirements

-   Python 3.11+
-   Python virtual environment
-   required Python dependencies
-   required API credentials stored locally in `.env`

Do not commit `.env` or API credentials to source control.

Start the development service with:

``` bash
./run.sh
```

The default local address is:

``` text
http://127.0.0.1:8001
```

Health check:

``` text
http://127.0.0.1:8001/health
```

FastAPI documentation:

``` text
http://127.0.0.1:8001/docs
```

A different port can be supplied when starting the service:

``` bash
./run.sh 8000
```

### Tests

Run the offline suite with the repository's virtual environment (no database or
network needed; two integration tests skip without credentials):

``` bash
venv/bin/python -m pytest tests
```

Last result, 2026-10-07: 801 passed, 2 skipped (`python scripts/release_gate.py` runs the same suite plus static checks). Run `tests/` only: the script
`vera/m6/test_m6_schema_sync.py` is not a pytest module and exits at import.
Integration paths that touch the database write to the shared production
instance, so use identifiable, removable test rows only.

### Demo page

``` bash
./run_demo.sh            # Streamlit demo page, port 8502
VERA_DEMO_SOURCE=fixture ./run_demo.sh   # force the labelled fixture
```

It loads the latest evaluated run from Postgres and otherwise falls back to a
clearly labelled fixture.

### Environment variables and database accounts (descriptions only)

`.env.example` lists the core variables with no values (other names read by the code are noted
there as comments); real values live only in the gitignored `.env`. Never commit `.env` or put a
secret in `.env.example`.

-   `OPENAI_API_KEY`: model provider key (generator and baseline). No Anthropic key will be used (A2 dropped 2026-10-02).
-   No search key: M2 search is keyless (arXiv abstract pages, `vera/search_providers.py`; config `search` in `config/vera_eval_run.json`). An optional agent-prepared seed list can be frozen by sha256 as a disclosed fallback (`search.fallback_seed`). A licence gate (`vera/licence_gate.py`) defers undeclared and rejects NC/ND licences before content is stored.
-   `GROQ_API_KEY` / `MISTRAL_API_KEY`: judge provider keys (`vera/m6/judge.py`); the judge default is Groq.
    `GROQ_API_KEY` also makes `/ask` free-tier-first (item #77, `config/ask-provider-chain.json`); API service only.
-   Optional, read by code: `VERA_COST_LOG` (file the M2 runner appends cost lines to),
    `VERA_JUDGE_*` overrides (model, price, `VERA_JUDGE_ALLOW_SAME_FAMILY=1` to allow a disclosed same-family judge),
    `VERA_DEMO_SOURCE`.
-   `VERA_API_KEY`: key required by `POST /ask`.
-   `EXTERNAL_DB_URL` / `INTERNAL_DB_URL`: Render Postgres URLs. They point at the
    **same** instance, and dev and production share one schema (`vera_vjay`), so
    "local" database work touches production data. Since 2026-10-07 both use VERA's own
    `vera_claude_code_rw` account (they previously used an AI-Internship account, which is refused on
    `vera_vjay`).
-   `VERA_DB_URL_RW`: `vera_claude_code_rw` URL for the MVP runner and preflight (`vera.db.get_role_engine`).
-   `VERA_DB_URL_WO`: `vera_pipeline_wo` URL for `/ask` corpus admission (item #79); unset = disabled.
-   `GROQ_API_KEY`: also makes `/ask` free-tier-first (item #77). `.env.example` lists every variable the
    code reads (names only); the gitignored `.env` holds the values.
-   `VERA_DB_PASSWORD_<role>`: one password variable for each of three accounts
    applied 2026-10-01 by the DB admin identity (`db/accounts/create_vera_accounts.sql`):
    `vera_claude_code_rw` (dev read/write), `vera_pipeline_wo` (production write-only,
    column-level SELECT on key columns only), `vera_eval_ro` (production read-only).
    No further accounts are to be created. 2026-10-07: all three logins verified; the write-only grants were
    exercised for corpus admission in a rolled-back transaction (plain INSERT ... RETURNING works; ON CONFLICT
    is refused because it needs SELECT on the conflict columns). `tests/test_m4_m5_integration.py` still
    imports another project's admin engine (skipped; open item).

## Deploying on Render (2026-10-05)

One image (`Dockerfile`) runs both services; `start.sh api|ui` picks which. Port: Render's `PORT`, else 8000. Secrets live only in Render's environment settings, never in the repo or the image (`.dockerignore` keeps `.env` and `*-prv` files out). Service URLs are not recorded in this repository.

1. Generate a client key locally: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`.
2. **API service:** New → Web Service → this repo, branch `main`; Runtime Docker; Root Directory blank; plan Free; Health Check Path `/health`; Auto-Deploy Off. Environment: `OPENAI_API_KEY`, `VERA_API_KEY` (the new key), optional `GROQ_API_KEY` (free-tier `/ask`, OpenAI as fallback), optional `VERA_DB_URL_WO` (corpus admission: Render's INTERNAL database URL with the `vera_pipeline_wo` account). Optional `VERA_DB_URL_RO` (sidebar corpus description: Render's INTERNAL database URL with `vera_eval_ro`). Leave `VERA_PUBLIC_MODE` unset (public mode is the default). Template: `.env.render.api.example` (copy to the gitignored `.env.render.api`, fill in, paste with "Add from .env").
3. **UI service:** New → Web Service → same repo; Runtime Docker; plan Free; Docker Command `./start.sh ui`; Health Check Path `/_stcore/health`; Auto-Deploy Off. Environment: `VERA_API_BASE_URL` (the API service's `https://` address, no trailing slash; without it the UI calls `127.0.0.1:8001` and fails), `VERA_API_KEY` (same key), `VERA_DEMO_SOURCE=fixture` (demo pages show the labelled fixture; no database on Render yet). Template: `.env.render.ui.example` (copy to `.env.render.ui`, same steps). The UI holds no provider key (no `OPENAI_API_KEY` or `GROQ_API_KEY`): it only calls the API, which chooses the provider.
4. Check: API `/health` returns 200 and `/ask` without the key returns 401; the UI answers one question. With `GROQ_API_KEY` set, the answer's `model` field reads `groq:...` and `cost_usd` is 0; `gpt-4.1-nano` there means Groq failed and OpenAI answered. An in-scope answer lists its numbered sources; with `VERA_DB_URL_WO` set, the API log shows a `corpus admission:` line per grounded answer.
5. Redeploy after a push: Manual Deploy → Deploy latest commit.

Limits: free services sleep when idle (first request after sleep waits about a minute); grounded `/ask` adds live search and link following (measured 2 to 4 s locally; bounded by the `grounding` and `resolve` deadlines; the UI waits up to 60 s); public-mode caps are in memory, so they reset whenever a service restarts or wakes; one uvicorn worker by design. Run `python scripts/release_gate.py` before every deploy.

## Week 4: TRACE evaluation (2026-10-04)

The bootcamp's Week 4 asks for "an eval suite your capstone runs against, visible from a Streamlit UI". This section is that suite, run on VERA itself: Trace, Read, Analyze, Codify, Enforce.

- **What was traced.** 30 frozen questions (`config/trace_questions_v1.json`: 12 in-scope, 5 multi-part, 5 false-premise, 4 out-of-scope, 4 ambiguous; 20 dev, 10 held-out; agent-authored, 5 seeded from the frozen VERA question). Two variants, both live calls to `gpt-4.1-nano`: **baseline** is exactly what `POST /ask` sends today (the question only, no retrieval); **grounded_v1** first runs VERA's keyless arXiv search (M2) and gives the model up to 5 numbered abstracts with a cite-only-these rule. Harness: `scripts/trace_capture.py`. Raw traces stay local (`tmp/trace_eval/`, gitignored: they hold full abstracts).
- **Read and Analyze.** Every dev trace was read and open-coded before any check was written (`docs/trace_eval/open_coding_baseline_v1.md`, `open_coding_grounded_v1.md`). Baseline failures: no verifiable citation (16/20), "studies show" with no study named (11/20), answers outside the 2023-2026 window (5/20), fabricated or placeholder citations (4/20), false premises accepted, out-of-scope requests answered (including a medicine dose). Saturation was not reached in 40 traces.
- **Codify.** Nine deterministic checks (`vera/trace_eval/checks.py`, `trace-checks-v1`), applied by question category. Results: `scripts/trace_measure.py` writes `eval_results/trace_eval_v1.json`.
- **Validated, not trusted.** An independent labeller, blind to the check results, labelled the 40 dev traces. Each check's TPR and TNR (positive = failure) is in `eval_results/trace_eval_v1_validation.json` (`scripts/trace_validate.py`). The checks catch almost every labelled failure (TPR 0.95-1.0) but over-flag some passes (TNR 0.5-0.75 on four checks). The word-overlap support heuristic missed all 3 partially supported sentences (TPR 0.0), so it is not a support check.
- **Measured result (all applicable checks pass; capture errors count as failures; Wilson 95% intervals; directional, small n).** Baseline: dev 2/20 (10%), held-out 2/10 (20%). Grounded_v1: dev 3/20 (15%), held-out 2/10 (20%). The headline barely moves, but the failure mix changes: by the blind labels, fabricated citations, unsourced numbers and vague "studies show" claims fall from 3, 3 and 12 dev traces to 0, 0 and 0. The new top failure is **retrieval**: in 13 of 19 grounded dev traces at most 1 of 5 arXiv results was on topic, and the model then (correctly) declined to answer from them (9/19). Out-of-scope, false-premise and ambiguity handling did not improve.
- **What TRACE found in VERA's code.** `search_question()` rebuilds its provider chain, and so the arXiv rate gate, on every call; multi-question runs hit HTTP 429 (arXiv also refuses after about 20 quick requests). The harness reuses one chain; the M2 gate defect is fixed (item #71: one cached chain per process). One grounded trace stayed a capture error after bounded retries.
- **Why retrieval misses (diagnosed 2026-10-04).** Mostly the question-to-query step, not the corpus: the query keeps the question's first words, so meta-words such as "published", "evidence" and "show" dominate and match almost any paper (on average 0.82 of 5 results on topic over 22 questions). Hand-focused queries on the same questions found relevant studies. Narrow questions and non-arXiv literature are smaller factors. Evidence: `docs/trace_eval/retrieval_diagnosis_2026-10-04.md`. Fixed in code by item #71 (query translation, OpenAlex second provider, rank-fusion fan-out); the after-fix measurement has not been run yet.
- **Search providers.** arXiv and OpenAlex, plus DOAJ when enabled (scholarly, keyless, merged by reciprocal rank fusion; DOAJ article metadata is released under a CC0 waiver, and VERA keeps only title, abstract and bibliographic fields from it, within a 2 requests per second limit and a daily cap), plus DuckDuckGo Lite as a **discovery-only** provider (item #71): it is used to find source URLs (mainstream news and journal portals without open search APIs, through `site:` groups in `config/vera_eval_run.json` `search.duckduckgo_lite`). VERA keeps only the target URL, the target page's own headline and its domain; it never shows DuckDuckGo snippets, pages or ranking, never auto-fetches discovered pages (no licence is declared, so the licence gate holds them for review), caps them at 2 of the final results, and labels news as grey literature. DuckDuckGo's params page says its parameters are intended for individual use; VERA uses it at low volume (5 s gap, daily cap of 8 queries, and a local per-question cache of URLs and headlines only under the gitignored `tmp/search_cache/`) and treats a challenge page as a failure, never evading it. Switch it off with `search.duckduckgo_lite.enabled: false`. **Google Scholar is a link-out only:** the demo page shows a "Search Google Scholar yourself" button built from VERA's query terms; the person clicks it in their own browser, and VERA never queries, fetches or parses Google Scholar, because Scholar's robots.txt disallows `/scholar` and Google's terms forbid automated access against robots.txt.
- **See it.** `streamlit run streamlit_app.py`, page **trace eval**: headline, per-check and validation tables, decision guidance (2026-10-07: paired exact McNemar tests per split and per check, Wilson intervals for check TPR/TNR, indicators and the formulas, thresholds in `config/trace_eval_guidance.json`), and a trace browser. On this snapshot only citation presence (p = 0.0039) and phantom evidence (p = 0.0002) improve significantly; the overall pass rate is not distinguishable.
- **Limits.** Agent-authored questions (self-preference risk); a single agent coder and labeller from the same model family as the builder; 30 questions; abstracts only; the checks were frozen before the after-fix run but are heuristics. Next fix by this evidence: retrieval query translation, then scope routing.

## Status and limitations (2026-10-04, updated 2026-10-07)

Written as dated observations, not guarantees. Every measured figure carries its caveat; nothing here is a statistical claim.

**What VERA does now**

- **Grounded `/ask` (2026-10-07, item #79; built and tested, not yet deployed).** Live search per accepted question, link-only results followed to original papers, answers only from retrieved abstracts with [n] citations, invalid citation numbers removed, sources listed under the answer, an explicit no-sources reply instead of memory answers; corpus admission (Gate A + licence gate) after the response. See "Grounded `/ask`" above. It does not yet meet every criterion R1 set for the public default (next list).
- **Free-tier-first models for `/ask`** (item #77): Groq `openai/gpt-oss-20b`, then `openai/gpt-oss-120b`, then OpenAI `gpt-4.1-nano`; evaluation paths stay on `gpt-4.1-nano`.
- **"What VERA draws on" sidebar** (item #78) on every page: scope, how answers are produced, and the Trace Eval evidence snapshot, read from shipped files.
- **Corpus description and connection triage** (item #83, ported from AI-Internship). `GET /corpus-summary` (behind `VERA_API_KEY`; the UI calls it server-side) describes VERA's own admitted sources in model-written prose with topics, from titles and metadata only, through the read-only account (`VERA_DB_URL_RO`); it is regenerated only when the source count, newest source time or prompt version change (memory cache; deterministic fallback with a retry cooldown) and shown in the sidebar. When the Ask page cannot reach the API, it shows an ordered, host-free triage (address, reachable, awake, `/health`, endpoint) stopping at the earliest failing step.

- **Search providers.** arXiv and OpenAlex (keyless, merged by reciprocal rank fusion). A DOAJ provider exists but is switched off in config: in two blind measurements (2026-10-04) it added no directly relevant result the others missed, and in the second it displaced two relevant ones. Zero-hit query relaxation is also built but off: it lowered strict relevance (directional, one labeller, 22 questions). DuckDuckGo Lite is **discovery-only**: VERA keeps only the target URL, that page's own headline and its domain, at low volume (5 s gap, daily cap of 8 queries, at most 2 of the top 5 results; a challenge page counts as a failure and is never evaded). DuckDuckGo's params page says its parameters are intended for individual use; that terms note is why volume stays low and the provider can be switched off (`search.duckduckgo_lite.enabled: false`). Discovered pages are not auto-fetched. **Google Scholar is a link-out only**: a person clicks a button in their own browser; VERA never queries it. Measured on 22 questions, one AI labeller (item #71, before the OpenAlex and DOAJ additions are separated out): strictly relevant results in the top 5 rose from 0.27 to 0.77 per question; directional, small n, not re-measured since.
- **Scope router** (`vera/scope_router.py`, `config/scope_router.json`). A deterministic first layer plus an optional small-model classifier; declined questions never reach search or the answering model. On the frozen 50-item scope set (`config/scope_set_v1.json`, sha256-frozen, AI-authored): false refusals 1/24 (Wilson 95% 0.007 to 0.202) and false accepts 0/26 (0.000 to 0.129), identical for layer 1 alone and with the classifier. **Directional, small n.** The one false refusal cites a 2025 study that the classifier called a future date.
- **Public mode and caps** (`vera/public_mode.py`, `config/public_mode.json`). Public mode is the default when `VERA_PUBLIC_MODE` is unset. The upstream URL comes from server configuration only, the key stays server-side and is never put in a widget, request and daily-cost caps return a generic 429 with no provider text, and model text is rendered through `safe_markdown`. Caps today are proposals: 6 requests per minute and 40 per day per client, 400 per day overall, USD 2.00 per day overall and USD 0.25 per client.
- **Licence rule (approved by R1, 2026-10-04).** The gate rejects only ND, no-educational-use and fee-only terms; plain NC is accepted; an undeclared or unclear licence is held for review. Checked on 7 hand-written cases (`vera/licence_gate.py`).
- **Release gate** (`python scripts/release_gate.py`). Offline: full suite, sha256 of the two frozen question files, static safety checks (no environment key passed to a widget, no `unsafe_allow_html` on model text, public mode default). `--live` additionally re-runs scope layer 1 only (zero cost) and fails on any false accept (directional, small n).

## How VERA remembers (Week 5)

**What it keeps.** VERA keeps checked research findings, not people. A finding is one sentence from an answer. The claim checker marked it supported by the abstract it cites. It comes with its sources. VERA never keeps your question, who you are, or any session id.

**How it gets in.** Findings are auto-saved shortly after the answer, in the background after the cited source is admitted to the corpus. They pass the claim check and the structural write gate with no human review — a recorded divergence from the Week 5 lesson's "confirm consequential writes". An owner-only confirm step is planned. The gate tests for support, allowed sources (arXiv or OpenAlex, licence accepted), identifier, and refusable content (tool dumps, instructions, personal remarks, echoed questions, time-bound claims).

**Where it lives.** In VERA's Postgres database, in the existing claims, answers and evidence tables, under one fixed memory label. Process memory holds no candidates.

**How it comes back.** On later questions, VERA searches saved findings by text match and recency, using the read-only account. Only findings above a minimum relevance floor are shown after the answer under "From VERA's memory", with their date and source. They are displayed only; they are never fed back to the model.

**How it is forgotten.** Findings older than 30 days are not recalled. Older findings rank lower, with a 14-day half-life. An operator can mark a finding contradicted, and it stops being recalled at once. Permanent deletion needs the owner's approval each time.

**Known limits.** Stored text is the model's own sentence checked against an abstract, so a fluent false claim from a bad abstract could pass. The gate is hygiene, not a poisoning defence. When a claim cites multiple sources, one evidence span is kept per source. The daily cap (50 findings per day) is a soft per-process cap. Memory lasts until the course database expires 2026-10-17. Database operations have a 5-second connect timeout and 5-second statement timeout. The UI shows no "Saved N findings" message because findings are saved asynchronously after the response; they appear on later questions.

**What VERA does NOT do yet**

- The full pipeline (M2 to M6) has **not been run live end to end**; the tests use fakes and fixtures.
- The central claim (VERA's engineered answer beats a direct model answer) is **unmeasured**.
- Grounded `/ask` (2026-10-07) now meets R1's criteria for the public default, measured once (directional, small n): each cited source is a record retrieved in that request with provider, identifier, retrieval time and licence decision; citations that map to no record are removed; an answer with no valid citation becomes an insufficient-evidence reply; each cited claim is checked against the cited abstract (`vera/claim_check.py`; unsupported sentences removed, partial ones marked; a different-family checker first; fails closed). On the 30-question trace set (`scripts/grounded_trace_run.py`, `eval_results/grounded_ask_v1.json`): unresolvable citations 0 of 57; unsupported-claim rate 9 of 105 (8.6%, Wilson 95% 4.6% to 15.5%), removed before display; partial or unsupported 37 of 105 (35%, 26.8% to 44.7%). Caveats: the checker's own error rate is unmeasured; abstracts only; false-premise questions often end as insufficient-evidence replies (corrections without citations).
- The API and UI are deployed on Render (2026-10-07, item #73; addresses are not recorded here); the deployed version predates grounded `/ask`.

**Accepted residuals (risks named, not removed)**

- A poisoned or misleading abstract from an allowed source is not detected (OWASP LLM04 and LLM08).
- Misinformation (LLM09): grounded `/ask` checks each cited sentence against the cited abstract with a model (`vera/claim_check.py`); the checker's own error rate is unmeasured, it sees abstracts only, and sentences without a citation are not checked. The trace-eval support heuristic (A6) remains unusable (TPR 0%).
- Corpus admission writes to the shared production database from visitor-driven searches (sources only, never visitor text), bounded by the request caps and by Gate A and the licence gate.
- Clients behind one IP share a limit (identity is the remote address; proxy headers are off by default).
- The title-family dedupe key can merge two different papers with the same main title in the same year; every merge is logged with its reason, so a wrong merge is visible.
- Some `/ask` 401/402/429 error details still name the provider.
- Links inside model answers are not validated beyond the citation check (LLM05).

## Current Status

*Last revised 2026-10-02 (R7a author, R11a record role; corrections from the 2026-10-02 code read).
Canonical, maintained status lives in `AI-Internship/p3m3/VERA-TODO-DIGEST.md` (sibling repo, gitignored
planning folder; a plain path, not a link); this section is a summary and can lag it.*

VERA is under active development as a capstone project. The 2026-09-30 directive lifted the earlier
"paused until 2026-10-15" rule; the Oct 15 - Nov 1 sprint plan is now the **fallback**, not the build window.

| Area | State (2026-10-01, corrected 2026-10-02; rows marked 2026-10-07 updated) |
|---|---|
| Architecture and design | Complete: `docs/vera-design.md` and Addendum A (milestone status table with the 2026-10-01 addendum at A.11). |
| Service foundation | 2026-10-07: FastAPI `GET /health`, `POST /ask` (grounded, items #77/#79) and `GET /corpus-summary` (item #83); deployed on Render (item #73; the deployed build predates items #79 and #83 until the next deploy). |
| Persistence | Built: Postgres schema `vera_vjay`, migrations 001-005 in `db/migrations/` (see `db/README.md`; 003 and 004 are not re-runnable). Migration 005 columns verified to exist live, read-only. (The earlier "persistence not yet implemented" line was stale.) |
| M1-M7 code | Built under `vera/` (m2_runner, m3, m4, m5, m6, m7, plus `pipeline_llm`, `pipeline_store`, `cost_ledger`) with tests. **The pipeline cannot yet run end to end**; nothing has run end to end against the live database. Missing: (a) no production code creates `runs` rows (only tests do), and the M6 adapter reads `runs.question` / `runs.final_response`, which nothing writes (`finalize_run` writes `engineered_response`), so the M6 CLI fails on a new run; (b) `sub_question_ids` is read by Gate C and the context builder but set by nothing (no M3-to-M4 adapter), so Gate C returns `insufficient`; (c) the runners are not repointed to the new accounts, and `run_m2` probably cannot run under the write-only account (static reading, not run live). The plan is `AI-Internship/p3m3/vera-plan-end-to-end-runner.md`. |
| What is persisted | Gate C decisions per attempt (`gate_c_decisions`), claims with fine-grained status and issue codes, answers by stage with tokens, cost and latency, relations (type and confidence only), appraisals with rubric/policy version, and immutable source versions. **M2 search cost is not persisted on `search_iterations`**: it is returned in memory and appended to a file only if `VERA_COST_LOG` is set. The inputs behind an M5 `weak` label are not stored. Live rows were not queried 2026-10-02. |
| Tests | 2026-10-07: `pytest tests`: **801 passed, 2 skipped**; release gate PASS. Includes the SQL contract test `tests/test_sql_contract.py`, which now runs live read-only with VERA's own `vera_eval_ro` (3 passed). |
| DB accounts | 3 accounts applied 2026-10-01 (descriptions above). 2026-10-07: all three logins verified; `.env` uses VERA's own accounts only (`EXTERNAL_DB_URL`/`INTERNAL_DB_URL`/`VERA_DB_URL_RW` → `vera_claude_code_rw`, `VERA_DB_URL_WO` → `vera_pipeline_wo`, `VERA_DB_URL_RO` → `vera_eval_ro`); write-only grants exercised for corpus admission. The pipeline runners are not yet repointed. |
| Version control | 2026-10-07: `main` is pushed to GitHub through the `/ask` provider chain (item #77); later work (grounded `/ask`, corpus admission and description, triage, Trace Eval guidance, sidebar) is committed only on R1's request. |
| Evaluation design | Longitudinal and quarterly: 8 runs, one per quarter (default stamps Jan 2025, Apr 2025, Jul 2025, Oct 2025, Jan 2026, Apr 2026, Jul 2026, Oct 2026; **unconfirmed**), 2 tests per agent/model per run, as-of stamping by code (never in the baseline prompt), a config fingerprint, and six named contamination channels (search, fetched content, parametric knowledge, judge hindsight, rubric hindsight, cross-run carry-over). Design only: no code or schema for it exists yet. See `AI-Internship/p3m3/VERA-EVAL-BEST-PRACTICES.md` (plain path; gitignored folder). |
| Target | Course end 2026-10-25 (corrected 2026-10-05; earlier documents say 10-12). Demo Day uses the Render deployment. |

**Open items (visibly open unless marked decided):** demo question (D0); baseline prompt lock (G2);
A2 (Anthropic key) DECIDED 2026-10-02 by R1: dropped, no Anthropic key will be used; MVP must-have #8
("draft critiqued"): direction given 2026-10-02 (a critique pass informed by the divergences found by claim
verification, feeding the existing bounded revision), plan being drafted, nothing built; deleting test row `questions.question_id=7` (needs an approved action); confirming
the 8 quarterly stamps; the staged live run; requirements freeze; provider-chain wiring for the
pipeline stages (`/ask` is wired since item #77, 2026-10-07); pg_dump and the non-Render host choice
(deferred to 2026-10-13..16; the Render database expires 2026-10-17; PostgreSQL stays regardless of host).

**Accepted divergences (recorded):** dev and production share one Postgres instance and schema
(separated by account only); the DB admin login is Render's original, misnamed identity; the
Render server default for password hashing is md5 (Render-managed) while the three new roles were
set with SCRAM-SHA-256 per session.

## Current status and plans

Plans and research exist as documents only; none is implemented unless stated. They live in the sibling
`AI-Internship` repository's local `p3m3/` folder (gitignored planning in another repo, so they are given as
plain paths and are not links):

-   `AI-Internship/p3m3/vera-plan-end-to-end-runner.md`: what is missing for a first end-to-end run and how to build it.
-   `AI-Internship/p3m3/vera-plan-config-single-source.md`: fix the three VERA config issues (model and judge choice
    scattered across code, an unread provider-chain file (removed 2026-10-07; `/ask` now uses `config/ask-provider-chain.json`), hardcoded judge family) with one config source,
    **planned before the MVP**; implementation not started, waiting on two R1 decisions (amend in place or a
    companion file; judge provider and key).
-   `AI-Internship/p3m3/vera-plan-m2-hardening.md`, `vera-plan-m3-gate-b-extras.md`,
    `vera-plan-m7-demo-narrative-traceability.md`, `vera-plan-cost-accounting-source-of-truth.md`,
    `vera-plan-verifier-judge-disagreement.md`, `orchestration-learning-and-critique-plan.md`: milestone
    hardening, cost accounting, judge/verifier disagreement, and the critique pass (direction D1).

Hard dates: MVP target Fri 2026-10-03 (aggressive); course end Mon 2026-10-12; `pg_dump` and host choice
2026-10-13 to 2026-10-16; fallback sprint start Thu 2026-10-15; the Render database expires Sat 2026-10-17.

## Documentation Index

| Document | What it holds |
|---|---|
| [docs/README.md](docs/README.md) | Index of this repository's design documents. |
| [docs/vera-design.md](docs/vera-design.md) | Full design, invariants, and Addendum A (MVP milestones, status table, A.11 status and replan). |
| [docs/VERA-OCT-15-SPRINT-PLAN.md](docs/VERA-OCT-15-SPRINT-PLAN.md) | Fallback Oct 15 - Nov 1 sprint plan (superseded as the build window). |
| [db/README.md](db/README.md) | Schema walkthrough, migration order and re-run rules, account and password-hashing notes, live verification. |
| [.env.example](.env.example) | Environment variables and accounts, described without secrets. |

Planning records live in the sibling `AI-Internship/p3m3/` directory (gitignored, so plain paths, not links):

-   `VERA-TODO-DIGEST.md`: canonical status, task table, critical path.
-   `VERA-CAPSTONE-PLAN.md` and `VERA-CAPSTONE-FLOWS-AND-PSEUDOCODE.md`: plan, flows, accepted divergences.
-   `VERA-ROUND-1-IMPLEMENTATION-SUMMARY.md` and `VERA_STATUS_REEXAMINATION_2026-09-30.md`: Round 1 record and an earlier (superseded) status snapshot.
-   `VERA-STATE-REPORT-2026-10-01.md`: git state, proposed commit groups, pre-commit checklist.
-   `VERA-EVAL-BEST-PRACTICES.md`: longitudinal evaluation design, contamination channels, source and licence rules.

### History archives (pre-edit copies)

Dated folders under `AI-Internship/p3m3/history/` (plain paths): `2026-10-01-cleanup-archive-10` (latest pass; copies of
this README, `db/README.md`, `.env.example` and `environment-log-prv.md` with the prefix `vera-repo-`),
`-archive-9`, `-archive-8`, `-archive-7`, `-archive-6` (earlier VERA README, docs, db README and `.env.example` copies),
`-archive-5`, `-archive-4`, `-archive-3`, `-archive-2`, and `2026-10-01-cleanup-archive`.

## Demo-Day Success Criterion

The project succeeds if VERA can demonstrate that it:

> produces a grounded research response significantly superior in
> quality to direct responses to the same research question from GPT-6
> Astra and other leading LLMs, while making its evidence-selection
> process inspectable and auditable.

Every consequential evidence decision should be traceable to its source,
evidence, provenance, and evaluation method.

A sophisticated and auditable process that produces an inferior research
answer does not satisfy the project's success criterion.

## Public Disclosure Boundary

This repository is publicly accessible for educational demonstration,
evaluation, and portfolio purposes.

It describes VERA's purpose, public capabilities, interfaces,
development status, and evaluation objectives. It intentionally does not
document proprietary internal representations, decision structures,
scoring methods, algorithms, orchestration, feedback mechanisms, private
architectures, or other non-public implementation details.

Public availability of this repository should not be interpreted as
disclosure of those non-public mechanisms.

## Project

**VERA: Verifiable Evidence-based Research Answers**

TAI Labs Agentic AI Engineering Capstone\
2026

Copyright © 2026 Tagg Maiwald. All rights reserved.
