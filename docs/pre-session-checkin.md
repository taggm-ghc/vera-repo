# TAI Labs Agentic AI Engineering Pre-session check-in — Tagg Maiwald

> **[Annotation 2026-10-09b (R11a, job C5-VERA): superseding status.** Observed today (decisions-2026-10-09.md; VERA git log read 2026-10-09): VERA redeployed by R1 and live check plus memory drill passed (week5-submission-record.md); VERA `main` = `50644f0` (D6, #91 scaffold; /version at 69cd936; polish committed); Week 5 assignment COMPLETED (R1); Demo Day date ignored, its outcomes run ASAP; course end is 2026-10-25 (any '10-12 end' below is stale); D-029 accepted to 2026-10-25; Render is the course-scoped host only (VERA's future host is non-Render, Postgres stays; no DB backups per R1, portable SQL exports wanted, #99). Design direction (R1, 10-09): research stances are Researcher Agent flavors with their own SOPs/scripts; VERA stays a stance-neutral research service; a private VERA instance is under consideration (#98 A6). New: OEV-6..OEV-15 (VERA research-service opportunities, `AI-Internship/p3m3/oev-vera-research-service-siblings.md`) and R1 requirements for VERA fetch/extract/provenance (many MIME types and rendered-page text; author/contributor/editor/reviewer data incl. public emails; DOI and bibliographic identifiers; provenance aggregates over time to rank sources and RAG results). Current VERA status and open work: `p3m3/VERA-STATUS-2026-10-09b.md`; to-do digest: `AI-Internship/p3m3/VERA-TODO-DIGEST.md`. Pre-session record dated 8 Sep; unchanged.**]**

_8 September 2026_

| Item | Status |
| --- | --- |
| Coding agent | Claude Code |
| Python version | Python 3.12.3 |
| OpenAI | Key created (key **not** shared) |
| Capstone seed | A provenance-grounded agentic context-engineering system that discovers, critically evaluates, registers, and organizes evidence into an auditable reasoning context to produce research responses measurably superior to direct leading-LLM baselines. |
| Blocker (if any) | None identified, other than invested time and possible service-provider outages. |

---

## Capstone seed and project overview

### 1. What does it do?

Discovers and critically evaluates candidate web evidence, registers its provenance, determines what evidence is adequate and admissible, organizes it into an auditable reasoning context, and uses that context to produce and evaluate a grounded research response.

### 2. Who is it for?

A researcher, Tagg Maiwald, using AI to assemble an auditable evidence base for a bounded research question.

### 3. What is the single most important question or task it must handle well first?

Given a bounded research question, assemble and critically evaluate an adequate evidence base, determine what evidence should inform the model's reasoning context and why, and use it to produce a grounded response superior to a direct leading-LLM baseline.

### 4. What would make you proud to demo on Demo Day?

I would be proud to demonstrate that the system produces a grounded research response significantly superior in quality to direct responses to the same research question from GPT-6 Astra and other leading LLMs, while making its evidence-selection process inspectable and auditable. Every consequential evidence decision should be traceable to its source, evidence, provenance, and evaluation method.

> **Annotation 2026-10-04 (R11a orchestrator):** RECORD of 8 September. The Blocker row ('None identified') is superseded: as of 2026-10-04 the main measured problem is retrieval quality (see `vera-design.md`, 2026-10-04 annotation). No Anthropic key is used (dropped 2026-10-02).
