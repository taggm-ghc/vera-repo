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
```

`GET /health` provides a basic service health check.

`POST /ask` is the primary research-question interface and serves as the
entry point to VERA.

`POST /ask` is protected by an API key (`VERA_API_KEY`, described below). The
M2-M7 pipeline modules under `vera/` and the Streamlit demo page are separate
from this HTTP interface and are not yet wired into `/ask` (see Current Status).

## Model Choice

VERA currently uses OpenAI's `gpt-4.1-nano`. At this stage the deliverable
is a reliable, cost-observable `/ask` contract rather than answer quality
tuned across models, so the cheapest acceptable model is used rather than
a flagship one; this is revisited once response quality becomes a
load-bearing evaluation dimension.

Where the model name comes from today (read from code 2026-10-02): `vera/pipeline_llm.py` takes
the default from `config/model-selection.json` and falls back to a hardcoded `gpt-4.1-nano`;
`vera/gate_a.py` and `vera/m6/baseline_collection.py` hardcode `gpt-4.1-nano` themselves. A per-task
provider chain file (`.vera-provider-chain.json`) exists but no code reads it, and its model
availability and prices are unverified; wiring it is an open item (optional, C9).

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

Last result, as of 2026-10-01, not re-run since: 178 passed, 2 skipped. Run `tests/` only: the script
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
-   Optional, read by code: `VERA_COST_LOG` (file the M2 runner appends cost lines to),
    `VERA_JUDGE_*` overrides (model, price, `VERA_JUDGE_ALLOW_SAME_FAMILY=1` to allow a disclosed same-family judge),
    `VERA_DEMO_SOURCE`.
-   `VERA_API_KEY`: key required by `POST /ask`.
-   `EXTERNAL_DB_URL` / `INTERNAL_DB_URL`: Render Postgres URLs. They point at the
    **same** instance, and dev and production share one schema (`vera_vjay`), so
    "local" database work touches production data.
-   `VERA_DB_PASSWORD_<role>`: one password variable for each of three accounts
    applied 2026-10-01 by the DB admin identity (`db/accounts/create_vera_accounts.sql`):
    `vera_claude_code_rw` (dev read/write), `vera_pipeline_wo` (production write-only,
    column-level SELECT on key columns only), `vera_eval_ro` (production read-only).
    No further accounts are to be created. The runners are not yet repointed to them (they still use
    the admin identity), and the write-only column grants are untested against a live run.

## Current Status

*Last revised 2026-10-02 (R7a author, R11a record role; corrections from the 2026-10-02 code read).
Canonical, maintained status lives in `AI-Internship/p3m3/VERA-TODO-DIGEST.md` (sibling repo, gitignored
planning folder; a plain path, not a link); this section is a summary and can lag it.*

VERA is under active development as a capstone project. The 2026-09-30 directive lifted the earlier
"paused until 2026-10-15" rule; the Oct 15 - Nov 1 sprint plan is now the **fallback**, not the build window.

| Area | State (2026-10-01, corrected 2026-10-02) |
|---|---|
| Architecture and design | Complete: `docs/vera-design.md` and Addendum A (milestone status table with the 2026-10-01 addendum at A.11). |
| Service foundation | FastAPI `GET /health` and `POST /ask` work. |
| Persistence | Built: Postgres schema `vera_vjay`, migrations 001-005 in `db/migrations/` (see `db/README.md`; 003 and 004 are not re-runnable). Migration 005 columns verified to exist live, read-only. (The earlier "persistence not yet implemented" line was stale.) |
| M1-M7 code | Built under `vera/` (m2_runner, m3, m4, m5, m6, m7, plus `pipeline_llm`, `pipeline_store`, `cost_ledger`) with tests. **The pipeline cannot yet run end to end**; nothing has run end to end against the live database. Missing: (a) no production code creates `runs` rows (only tests do), and the M6 adapter reads `runs.question` / `runs.final_response`, which nothing writes (`finalize_run` writes `engineered_response`), so the M6 CLI fails on a new run; (b) `sub_question_ids` is read by Gate C and the context builder but set by nothing (no M3-to-M4 adapter), so Gate C returns `insufficient`; (c) the runners are not repointed to the new accounts, and `run_m2` probably cannot run under the write-only account (static reading, not run live). The plan is `AI-Internship/p3m3/vera-plan-end-to-end-runner.md`. |
| What is persisted | Gate C decisions per attempt (`gate_c_decisions`), claims with fine-grained status and issue codes, answers by stage with tokens, cost and latency, relations (type and confidence only), appraisals with rubric/policy version, and immutable source versions. **M2 search cost is not persisted on `search_iterations`**: it is returned in memory and appended to a file only if `VERA_COST_LOG` is set. The inputs behind an M5 `weak` label are not stored. Live rows were not queried 2026-10-02. |
| Tests | `pytest tests`: **178 passed, 2 skipped** (as of 2026-10-01, not re-run since). Includes the SQL contract test `tests/test_sql_contract.py` (87 table/column pairs). Older documents may say 166: that was the 2026-09-30 count before tests were added; the 12-test difference is not itemised. |
| DB accounts | 3 accounts applied 2026-10-01 (descriptions above). Column grants of the write-only account are untested against a live run; the runners are not yet repointed to the new accounts. |
| Version control | Only the B1 (`28aae11`) and B2 (`9fef487`) commits exist. M1-M7 code, migrations 001-004, the edit to 005, and the `.gitignore` edit are **uncommitted** (`venv/` was already ignored; `syllabus/` was removed from the working tree 2026-10-02 as irrelevant to VERA); commit only after the owner validates (checklist in `VERA-STATE-REPORT-2026-10-01.md`; M4 owns the migration 005 `evidence_relations.run_id` backfill that was removed, to be confirmed). |
| Evaluation design | Longitudinal and quarterly: 8 runs, one per quarter (default stamps Jan 2025, Apr 2025, Jul 2025, Oct 2025, Jan 2026, Apr 2026, Jul 2026, Oct 2026; **unconfirmed**), 2 tests per agent/model per run, as-of stamping by code (never in the baseline prompt), a config fingerprint, and six named contamination channels (search, fetched content, parametric knowledge, judge hindsight, rubric hindsight, cross-run carry-over). Design only: no code or schema for it exists yet. See `AI-Internship/p3m3/VERA-EVAL-BEST-PRACTICES.md` (plain path; gitignored folder). |
| Target | MVP target Oct 3, 2026 is aggressive (critical path about 9 h, about 12 h with contingency); fallback sprint Oct 15 - Nov 1; course end 2026-10-12. |

**Open items (visibly open unless marked decided):** demo question (D0); baseline prompt lock (G2);
A2 (Anthropic key) DECIDED 2026-10-02 by R1: dropped, no Anthropic key will be used; MVP must-have #8
("draft critiqued"): direction given 2026-10-02 (a critique pass informed by the divergences found by claim
verification, feeding the existing bounded revision), plan being drafted, nothing built; deleting test row `questions.question_id=7` (needs an approved action); confirming
the 8 quarterly stamps; the staged live run; requirements freeze; provider-chain wiring
(`.vera-provider-chain.json` exists but no code reads it; optional); pg_dump and the non-Render host choice
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
    scattered across code, an unread provider-chain file, hardcoded judge family) with one config source,
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
