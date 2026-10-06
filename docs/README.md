# VERA documentation index

*Rewritten 2026-10-01 (R7a author, R11a record role). This file previously duplicated the root
README; that copy is archived at
`../AI-Internship/p3m3/history/2026-10-01-cleanup-archive-6/vera__docs-README.md`. The project overview,
status, run instructions and environment description are in the root [README.md](../README.md).*

## Documents in this folder

Status tags: LIVE (current, maintained), RECORD (kept as written, dated annotations only), SUPERSEDED, BACKLOG (parked, not built). Listing verified against the directory 2026-10-02. Files named `*-prv.*` are private and gitignored (`.gitignore`: `*-prv.*`), so they exist locally only.

| Document | Purpose | Status |
|---|---|---|
| [vera-design.md](vera-design.md) | Full design, governing invariants, Addendum A (MVP boundary, milestone table, A.11 status and replan, status addendum). Original milestone targets preserved per the Provenance invariant. | LIVE |
| [VERA-OCT-15-SPRINT-PLAN.md](VERA-OCT-15-SPRINT-PLAN.md) | Oct 15 - Nov 1 sprint plan (2026-09-30). Fallback plan, superseded in part by the 2026-10-03 MVP target. | SUPERSEDED (in part; fallback) |
| [pre-session-checkin.md](pre-session-checkin.md) | Capstone seed and pre-session check-in (8 September 2026). | RECORD |
| [vera-v06-design-prv.md](vera-v06-design-prv.md) | Earlier private design, Refined Version 06 (9 September 2026); vera-design.md is current. | RECORD |
| [vera-retrieval-quality-digest-prv.md](vera-retrieval-quality-digest-prv.md) | Retrieval-quality layer digest (18 September); nothing implemented, deferred by A.9. [Corrected 2026-10-04: digest layer still unbuilt, but a search-level retrieval build (item #71) exists, uncommitted; see the digest's 2026-10-04 annotation.] | BACKLOG |
| [vera-retrieval-vocabulary-reconciliation-prv.md](vera-retrieval-vocabulary-reconciliation-prv.md) | Maps the digest's terms onto Gate A/B/C; still cited by vera-design.md A.9 (verified 2026-10-02). | LIVE (vocabulary only) |
| [vera-multimodal-extraction-backlog-prv.md](vera-multimodal-extraction-backlog-prv.md) | Parked OCR/table/figure extraction work; scope decision pending. | BACKLOG |
| [vera-privileged-mediation-annotated-bibliography-prv.md](vera-privileged-mediation-annotated-bibliography-prv.md) | Annotated bibliography for the privileged-mediation security framework (September 2026). Not reviewed in this pass; the file is root-owned and read-only to the maintainer, so it carries no annotation. | RECORD |
| `vera-eigenprojection-distribution-retrieval-design-prv.docx` | Word design note (24 September); not Markdown, not reviewed here. | RECORD (UNVERIFIED content) |

The design-notes files at the repo root (`../ask-guardrail-design-prv.md`, `../pricing-scraper-design-prv.md`) and the folders `../opencode.cli/` and `../refactor-prv/` are RECORD material; each has its own README or dated annotations.

Database documentation: [../db/README.md](../db/README.md). Environment variables and accounts, described
without secrets: [../.env.example](../.env.example).

## Planning records (sibling repo, `AI-Internship/p3m3/`)

Status, plan, flows, state report and the longitudinal evaluation design are listed with links in the
"Documentation Index" section of the root [README.md](../README.md), together with the dated history
archive folders (`2026-10-01-cleanup-archive` through `-archive-10`).

*Annotation 2026-10-02 (R11a, round 3): index completed (it previously omitted the private files) and status tags added. Pre-edit copy: `../AI-Internship/p3m3/history/2026-10-01-cleanup-archive-10/vera-repo-docs_README.md`. The pipeline cannot yet run end to end; live plans are in the sibling repo's local `AI-Internship/p3m3/`.*

*Annotation 2026-10-04 (R11a orchestrator): links verified against the directory. The bibliography file is root-owned and read-only; it was not annotated. Current status of the pipeline is in `vera-design.md` (2026-10-04 annotation).*
