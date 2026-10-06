# VERA Oct 15–Nov 1 Sprint Plan
**Date:** 2026-09-30 (Planning)  
**Sprint Window:** Oct 15 (kickoff) through Nov 1 (M7 demo hardening)  
**Strategy:** Infrastructure-First (A) + Narrow Research Question (D)  
**Total Effort:** 16–22 days (tight 11-day window requires focus, no rework)


> **Annotation 2026-10-01 (R7a author, R11a records): this plan is now the FALLBACK, not the build plan.** The R1 directive of 2026-09-30 lifted the pause and M1-M7 were built early (see `docs/vera-design.md` A.11 addendum and `AI-Internship/p3m3/VERA-TODO-DIGEST.md`). Track 1 (schema and round-trip test) is done in substance: the `vera_vjay` schema is live (migrations 001-005) and three DB accounts were applied 2026-10-01. Track 2 (demo question) is still OPEN (D0, undecided). Dates below are the original plan and are kept as written. Correction: the "11-day window" wording is wrong; Oct 15 to Nov 1 is 18 days inclusive (corrected in the p3m3 records 2026-10-01); Oct 15, 2026 is a Thursday. Pre-edit copy: `AI-Internship/p3m3/history/2026-10-01-cleanup-archive-6/vera__docs-VERA-OCT-15-SPRINT-PLAN.md`.

> **Annotation 2026-10-05 (R11a orchestrator): still the FALLBACK plan; dates and tracks below are as originally written. Since 2026-10-01: item #72 tranche 1 (scope router, public-mode access control, search fixes, licence gate aligned, release gate, README limitations) is built and uncommitted (HEAD e77e322 pushed; suite 724 passed, 1 skipped). Track 2 demo question: R1 approved the frozen anchor question D0 (2026-10-04 late), so it is no longer open. Not started: grounded `/ask` as public default (R1's citation existence and provenance conditions), the first live end-to-end run and M6 central-claim measurement, deployment (host deferred by R1), Week 5 memory. Course ends 2026-10-12; the Render database expires 2026-10-17. Details: AI-Internship `p3m3/item-72-vera-maturation.md` sections 7-8.**
>
> **Annotation 2026-10-02 (R11a, round 3):** the plan is SUPERSEDED IN PART by the 2026-10-03 MVP target (aggressive) and remains the fallback if that slips. The pipeline cannot yet run end to end. Live plans: `AI-Internship/p3m3/VERA-TODO-DIGEST.md` and the `AI-Internship/p3m3/vera-plan-*.md` files (sibling repo, local only). Any "Anthropic key" step is void (dropped 2026-10-02). Pre-edit copy: `AI-Internship/p3m3/history/2026-10-01-cleanup-archive-10/vera-repo-docs_VERA-OCT-15-SPRINT-PLAN.md`.

> **Annotation 2026-10-04 (R11a orchestrator): dates conflict with the course end; flagged, not changed.** The bootcamp ends 2026-10-12 and the Render database expires 2026-10-17, so the Oct 13-14 preparation and the Oct 15 - Nov 1 schedule below fall after the course end and partly after the database expiry. Whether VERA work continues after 2026-10-12 is not decided in this document. Status: M1-M7 exist; Week 4 TRACE on VERA is pushed (HEAD e77e322); the item #71 search build is uncommitted (suite 574 passed, 1 skipped). [Corrected 2026-10-04, late: suite is now 637 passed, 1 skipped; search is no longer a single API (arXiv, OpenAlex, DOAJ, DuckDuckGo Lite discovery only), so the M2 'Integrate search API' and 'two providers' lines below are built in substance; the Demo Day host is still undecided and a live URL is mandatory.] Tavily, if referenced below, is DROPPED. Live plans remain in the sibling repo's `AI-Internship/p3m3/`.

---

## Pre-Sprint Preparation (Oct 13–14)

Three parallel tracks complete independently by Oct 14 EOD. Both critical paths (T1 + T2) must finish before M2 starts Oct 15.

### Track 1: Infrastructure Setup (2–3 hours)
**Owner:** Sonnet (R7a) or Tagg (R5)  
**Deliverable:** vera_vjay schema created + round-trip tested

**Checklist:**
- [ ] Review vera-design.md sections 6–8 (Gates, success criteria)
- [ ] Design question/run/candidate/source table schema
- [ ] Test Postgres access (EXTERNAL_DB_URL works)
- [ ] Create migration scripts (SQL)
- [ ] Execute schema creation
- [ ] Run round-trip test (write question → read back)
- [ ] Verify persistence survives redeploy

**Unblocks:** M2 start (Oct 15 afternoon)

---

### Track 2: Research Question Selection (2–3 hours)
**Owner:** Tagg (R5) or other team member  
**Deliverable:** One bounded research question chosen + scoped

**Checklist:**
- [ ] Read vera-design.md (sections 1–8, emphasis on "Capstone seed")
- [ ] Read Addendum A (MVP boundary, success/fail rules)
- [ ] Generate 5–10 candidate research questions
- [ ] Evaluate against selection criteria:
  - [ ] Requires evidence integration (not single-source answerable)
  - [ ] Clear baseline (direct LLM response achievable)
  - [ ] Demonstrable gap (direct LLM likely missing key evidence)
  - [ ] Answerable in 2–3 day sprint window
  - [ ] Evaluation dimensions measurable
- [ ] Propose final question (with justification)
- [ ] Create Evidence Requirements Map (vera-design.md section 8)

**Selected question:** ___________________________  
**Unblocks:** M2 start (Oct 15 afternoon)

---

### Track 3: Evaluation Rubric Design (1–2 hours)
**Owner:** Same as Track 2 (part of research question work)  
**Deliverable:** Evaluation rubric + baseline collection plan

**Checklist:**
- [ ] Define 5 evaluation dimensions (from VERA-CAPSTONE-PLAN.md step 1a):
  - [ ] Relevance (evidence coverage %)
  - [ ] Grounding (claims traceable to source %)
  - [ ] Reasoning integrity (counterevidence addressed)
  - [ ] Cost/latency (API calls, time)
  - [ ] Auditability (decisions observable, 1–5 scale)
- [ ] Create scoring rubric (1–5 per dimension)
- [ ] Plan baseline collection (same question, direct model, same model as engineered)
- [ ] Document evaluation method (how to measure each dimension)

**Unblocks:** M6 baseline comparison (Oct 30–31)

---

## Sprint Schedule (Oct 15–Nov 1)

### Oct 15 (Thursday): Kickoff + M2 Start
**Morning:** Execute Track 1 + T2 verification (2–3 hours)
- Verify infrastructure setup (persistence round-trip)
- Confirm research question selected
- Prepare M2 work

**Afternoon:** M2 begins
- Search API integration
- Gate A scoring function

---

### Oct 15–19: M2 (Search + Gate A + Provenance)
**Owner:** Sonnet (R7a) + Tagg (R5)  
**Effort:** 3–5 days (timeline is tight)

| Task | Effort | Blockers |
|------|--------|----------|
| Integrate search API (Web Search or similar) | 1.5 days | API key, rate limits |
| Implement Gate A scoring (query fit, evidentiary value, cost/risk) | 1.5 days | Score formula design |
| Selective fetch + content hash + versioning | 1 day | Search candidates available |
| Source registry + provenance logging | 1 day | Fetch pipeline working |

**Exit Criteria:**
- Search returns ≥5 candidates per query
- Gate A scores each candidate (0–1)
- Fetch writes to source registry with content_hash + version
- Persistence verified (query back across redeploy)

**Unblocks:** M3 (Oct 20)

---

### Oct 20–24: M3 (Evidence Extraction + Gate B)
**Owner:** Sonnet (R7a)  
**Effort:** 3–5 days

| Task | Effort | Blockers |
|------|--------|----------|
| Semantic span extraction (evidence units with location) | 1.5 days | Source content parsing |
| Critical appraisal framework (6 dimensions) | 1.5 days | Rubric design clarity |
| Gate B admission logic (admit/qualify/reject/quarantine) | 1.5 days | Appraisal output available |

**Exit Criteria:**
- Evidence units linked to exact source spans (line/character offsets)
- Appraisal scores recorded (source/process, data quality, applicability, independence, uncertainty, temporal validity)
- Gate B decisions logged with rationale

**Unblocks:** M4 (Oct 25)

---

### Oct 25–27: M4 (Gate C + Context Construction)
**Owner:** Sonnet (R7a)  
**Effort:** 2–3 days

| Task | Effort | Blockers |
|------|--------|----------|
| Gate C adequacy check (coverage, independence, missingness) | 1 day | M3 output available |
| Evidence-relation graph (supports/refutes/qualifies) | 0.5 days | Evidence units + propositions |
| Reasoning context construction (compact, auditable) | 1 day | Relations graph complete |

**Exit Criteria:**
- Gate C returns `synthesize` / `search-again` / `insufficient`
- Evidence relations tracked
- Context package ready (provenance preserved, qualifications noted)

**Unblocks:** M5 (Oct 28)

---

### Oct 28–29: M5 (Synthesis + Revision)
**Owner:** Sonnet (R7a) + Tagg (R5)  
**Effort:** 2 days

| Task | Effort | Blockers |
|------|--------|----------|
| Grounded synthesis (draft response from context) | 1 day | Context package ready |
| Draft critique (completeness, grounding, inference) | 0.5 days | Draft generated |
| Bounded revision (fix material defects) | 0.5 days | Critique complete |

**Exit Criteria:**
- Engineered response generated (grounded, cites sources)
- Revision rationale recorded
- Response ready for baseline comparison

**Unblocks:** M6 (Oct 30)

---

### Oct 30–31: M6 (Baseline Comparison + Evaluation)
**Owner:** Sonnet (R7a) + Tagg (R5)  
**Effort:** 2 days

| Task | Effort | Blockers |
|------|--------|----------|
| Direct baseline response (same question, no engineered context) | 0.5 days | Question finalized |
| Comparative metrics (score all 5 dimensions) | 1 day | Eval rubric finalized (Track 3) |
| Eval rationale (why engineered exceeds or falls short) | 0.5 days | Metrics available |

**Exit Criteria (CRITICAL):**
- ✅ Engineered response wins ≥3 of 5 dimensions (at least one being relevance or grounding)
- ✅ OR recorded as "failed case" per Addendum A.9 (no false success)
- Both responses available for comparison
- Metrics documented

**Unblocks:** M7 (Nov 1)

---

### Nov 1 (Sunday): M7 (Demo Hardening)
**Owner:** Tagg (R5) + Sonnet  
**Effort:** 1–2 days

| Task | Effort | Blockers |
|------|--------|----------|
| Demo UI / walkthrough clarity | 0.5 days | Metrics from M6 |
| Observability (what was chosen/rejected/why) | 0.5 days | Decision log available |
| 3-minute narrative walkthrough | 0.5 days | Demo works end-to-end |

**Exit Criteria:**
- Demo understandable in ~3 minutes
- All decisions traceable
- Metrics visible
- **MVP ready (success or documented failure)**

---

## Parallel Opportunities

### Can M3 and M4 overlap?
**Partial:** M3 evidence extraction and M4 Gate C can start simultaneously once M2 completes. M4 needs M3 evidence units to compute relations graph, but both can start in parallel. **Recommendation:** Don't force overlap in 11-day window; sequential is safer.

### Can anyone else prep during M2–M5?
**Limited:** M2–M5 are sequential blockers. One Sonnet agent can do gate implementations in parallel while Tagg handles decision/eval work. **Recommendation:** Keep team focused; add parallelization only if one milestone completes early.

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Track 1 infrastructure delays** | Blocks entire sprint | Pre-schedule Postgres admin access; test Oct 12 |
| **Research question too hard** | M2–M3 overrun | Select from candidates with clear evidence gaps (Oct 14) |
| **Search API unreliable** | M2 blocked | Have 2 search providers available (Web Search + fallback) |
| **M6 response NOT superior** | MVP fails quality test | Record as "failed case" (Addendum A.9); don't force success |
| **11-day window too tight** | Cannot ship by Nov 1 | Cut scope: defer S1–S7 stretch items; narrow M4 loop; accept "beta" demo |
| **Team context loss (Oct 12–15)** | Ramp-up delay | Dry-run infrastructure Oct 12; confirm team availability Oct 14 |

---

## Success Criteria (MVP Go/No-Go)

### All Required (No Compensation)
1. ✅ One bounded research question completes M2–M7 workflow
2. ✅ Evidence discovered (Gate A candidates scored)
3. ✅ Evidence admitted/rejected (Gate B appraisal complete)
4. ✅ Evidence set adequate (Gate C check passed)
5. ✅ Context engineered (reasoning package built)
6. ✅ Response synthesized + critiqued + revised (M5)
7. ✅ Baseline collected + comparative metrics done (M6)
8. ✅ **Engineered response wins ≥3/5 dimensions** ← **GO/NO-GO GATE**
9. ✅ All decisions traceable (M7)
10. ✅ Demo understandable in ~3 minutes (M7)

### If Any Fail
- Response quality insufficient → Record as "failed case" (not "bad demo")
- Decisions not traceable → Grounding/auditability failed
- Evidence cannot map to source → MVP incomplete
- Cost/latency unacceptable → Value test failed

---

## Post-MVP Stretch Work (S1–S7, Only If Time Permits)

**Deferred per Addendum A.6 (not required for MVP):**
- S1: Exhaustive bias taxonomy
- S2: Full meta-drift (scope displacement + contextual relevance)
- S3: Multiple integrity detectors (poison/adversarial)
- S4: Lateral verification infrastructure
- S5: Evidence-independence graphs
- S6: Evaluator agreement / calibration
- S7: Multimodal ingestion (PDFs, images)

**Start date for S1–S7:** Only after M7 complete + MVP success confirmed

---

## Oct 15 Day-1 Kickoff Checklist

Before 9 AM Oct 15:
- [ ] Track 1 infrastructure verified (schema created, round-trip tested)
- [ ] Track 2 research question finalized
- [ ] Track 3 evaluation rubric ready
- [ ] Team confirmed (Sonnet available? Tagg available? Roles clear?)
- [ ] Search API key active + tested
- [ ] Postgres credentials verified
- [ ] Sprint board/tracking updated (M2–M7 tasks visible)
- [ ] Communication plan (daily standup? async?)

**Kickoff time:** Oct 15, 10 AM (allow 1 hour for verification)  
**M2 work begins:** Oct 15, 11 AM

---

**[Corrected 2026-10-04: stale; see the 2026-10-04 annotation at the top. This plan is the fallback and its dates post-date the 2026-10-12 course end.] Status: Oct 15 sprint is planned, tracked, and ready to execute. Infrastructure-First + Narrow Question strategy minimizes risk in tight 11-day window.**
