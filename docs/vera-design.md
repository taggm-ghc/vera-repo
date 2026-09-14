# VERA — Verifiable Evidence-based Research Answers

**Provenance-grounded agentic context engineering for auditable research synthesis**

Prepared September 2026

> This is the public design overview. It describes the text evidence-selection,
> critical-appraisal, reasoning, synthesis, evaluation, and provenance architecture
> implemented for the capstone.

---

## Capstone one-liner

VERA is a provenance-grounded agentic context-engineering system that discovers, critically evaluates, registers, and organizes evidence into an auditable reasoning context to produce research responses measurably superior to direct leading-LLM baselines.

## North star

The goal is to demonstrate that the system produces a grounded research response significantly superior in quality to direct responses to the same research question from leading frontier LLMs, while making its evidence-selection process inspectable and auditable. Every consequential evidence decision should be traceable to its source, evidence, provenance, and evaluation method.

## Design rationale

VERA's governing proposition is not "select defensible evidence" but "create demonstrable incremental research value." A well-grounded, auditable response that is materially worse than a direct frontier-model response fails the outcome test.

The architecture therefore treats critical inquiry, evidence-set adequacy, explicit inference, synthesis, answer evaluation, and bounded revision as first-class system stages rather than leaving final answer quality to the generating model.

## Scope

VERA is deliberately bounded to text. It does not address multimodal representations, universal ontologies, production malware analysis, or generalized autonomous research. Search, fetch, parsing, and model inference are treated as reusable tools; the engineered contribution is the reasoning context constructed between them. PostgreSQL is the canonical memory and audit store.

## Research foundations

| Research source | Transferable principle | How VERA applies it |
| --- | --- | --- |
| Facione critical-thinking framework [1] | Interpretation, analysis, evaluation, inference, explanation, and self-regulation are separable critical-thinking operations. | Explicit inference, explanation, and self-evaluation stages after evidence appraisal. |
| ACRL Framework [2] | Research is iterative inquiry; searching is nonlinear strategic exploration; authority is contextual; information creation is a process. | Evidence-needs decomposition, search iteration, process appraisal, and search-again behavior. |
| Cochrane search guidance [3] | High-recall search is preferable when missing relevant evidence would distort conclusions; multiple reports may derive from one underlying study. | Gate A biased toward recall; evidence lineage and independence tracking. |
| Wang & Strong data quality [4] | Data quality includes intrinsic, contextual, representational, and accessibility dimensions and is task-dependent. | Data quality, evidentiary quality, and applicability kept separate rather than one weight score. |
| CASP critical appraisal [5] | Trustworthiness, results/value, and relevance require systematic appraisal; venue or author alone is not enough. | Source/process and methodology appraisal with explicit unknown states. |
| GRADE/Cochrane evidence-body concepts [6] | Bodies of evidence require assessment of inconsistency, indirectness, imprecision, bias, and missingness. | Gate C evidence-set adequacy rather than judging only atomic passages. |
| Wineburg & McGrew lateral reading [7] | Professional fact-checkers verify unfamiliar sources using external sources rather than relying on the site itself. | Lateral source verification for consequential evidence. |
| Sperber et al. epistemic vigilance [8] | Source credibility and content/argument acceptability are distinct vigilance problems. | Source credibility, claim support, and inferential validity assessed separately. |
| PRISMA flow principle [9] | Identification, exclusion, inclusion, and reasons should remain traceable. | Candidate and exclusion histories preserved with reasons, without claiming PRISMA compliance. |

## Capstone seed

| Question | Answer |
| --- | --- |
| What does it do? | Discovers candidate evidence, identifies what evidence the question requires, selectively acquires and registers sources, critically appraises claims and source processes, models support and contradiction, determines whether the evidence set is adequate, constructs an auditable reasoning context, and generates and critiques a grounded response. |
| Who is it for? | A researcher using AI to assemble and reason over an auditable evidence base for a bounded research question. |
| What must it handle well first? | Given a bounded research question, what evidence is needed, which candidate evidence is worth acquiring, what evidence is trustworthy and applicable, whether the evidence set is sufficient, and what conclusions are warranted by it? |
| What would make a proud demo? | A grounded response measurably superior to direct leading-LLM baselines, with every consequential evidence and reasoning decision inspectable and traceable to source, evidence, provenance, method, and uncertainty. |

## Success and failure conditions

| Condition | Pass / fail rule |
| --- | --- |
| Response quality | PASS only if the capstone response materially exceeds a predeclared direct-model baseline on the evaluation dimensions that matter for the question. |
| Grounding | FAIL if consequential claims cannot be mapped to admitted evidence or if citations do not support the claims they accompany. |
| Reasoning integrity | FAIL if conclusions do not follow from evidence, material counterevidence is ignored, or uncertainty is hidden. |
| Auditability | FAIL if consequential acquisition, appraisal, admission, inference, exclusion, or revision decisions cannot be traced. |
| Incremental value | FAIL if the pipeline adds cost, latency, and complexity yet yields response quality no better than or worse than direct frontier-model baselines. |

> Demo success = superior response quality **AND** grounding **AND** reasoning integrity **AND** auditability. None of these compensates for failure of another.

## System boundary and workflow

The differentiated capability is context engineering, extended to include the critical-thinking operations required to turn evidence into a superior answer.

1. Accept a bounded research question and governing context.
2. Interpret the question and create an Evidence Requirements Map that specifies material subquestions, evidence types, temporal scope, authority needs, counterevidence needs, and coverage state.
3. Plan one or more search strategies and discover candidate sources.
4. **Gate A:** prioritize candidates before full acquisition using query fit, expected evidentiary value, source cues, novelty, cost/risk, and uncertainty, while favoring recall over premature exclusion.
5. Selectively fetch content into quarantine/staging; compute content hash and register source/version/provenance before semantic use.
6. Run bounded deterministic content-integrity checks and preserve exact finding spans.
7. Segment relevant content into semantic evidence units with exact source locations.
8. Critically appraise source/process, data quality, evidentiary quality, applicability, temporal validity, independence, uncertainty, meta-drift, and reference-relative bias where supported.
9. Perform lateral verification for consequential or unfamiliar sources and record external source-appraisal evidence.
10. **Gate B:** admit, qualify, reject, quarantine, or excise-span-and-admit individual evidence.
11. Build an evidence-relation and argument layer linking claims to supporting, contradicting, qualifying, and derivative evidence, explicit assumptions, and alternative interpretations.
12. **Gate C:** evaluate the evidence set as a whole for coverage, directness, independence, contradiction, currency, missingness, uncertainty, and diminishing-return saturation.
13. If Gate C fails adequacy, formulate the missing evidence need and iterate search rather than forcing synthesis.
14. Construct model context from evidence and argument structures, preserving provenance, qualification, counterevidence, and uncertainty.
15. Generate a deliberate draft synthesis.
16. Critically evaluate the draft for completeness, grounding, inferential validity, contradiction handling, qualification, scope fidelity, relevance, synthesis, and clarity.
17. Perform one bounded revision when material defects are detected.
18. Return the grounded response and persist decisions, findings, evidence links, answer evaluation, comparative baseline results, and feedback.

## Three decision gates

| Gate | Question | Primary output |
| --- | --- | --- |
| Gate A: acquisition priority | Is this candidate sufficiently likely to add relevant evidence to justify acquisition or later review? | `fetch` / `defer` / `reject`, with uncertainty and factors |
| Gate B: evidence admission | After provenance, integrity, critical appraisal, drift, epistemic and bias evaluation, may this evidence participate in reasoning? | `admit` / `qualify` / `reject` / `quarantine` / `excise-span-and-admit` |
| Gate C: evidence-set adequacy | Does the admitted evidence set cover the material needs of the question well enough to warrant synthesis? | `synthesize` / `search-again` / `answer-qualified` / `insufficient-evidence` |

Gate A controls acquisition resources, Gate B protects reasoning context, and Gate C protects answer adequacy.

## Evidence Requirements Map

Before search, VERA creates a machine-addressable representation of what would have to be established to answer the governing question well. This prevents high-volume retrieval from being mistaken for evidence completeness.

| Field | Purpose |
| --- | --- |
| Subquestion | Separates the governing question into material evidentiary needs without prematurely answering them. |
| Claim type | Identifies whether the requirement concerns fact, causal claim, comparison, forecast, definition, normative judgment, or another bounded type. |
| Desired evidence type | Guides search toward evidence capable of answering the requirement rather than merely mentioning the topic. |
| Temporal scope | Defines freshness and historical coverage required by the question. |
| Counterevidence need | Requires active search for evidence that could weaken or reverse a provisional conclusion. |
| Coverage state | `unsearched` / `partial` / `adequate` / `contradictory` / `unresolved` / `not-obtainable` |

## Search strategy and Gate A

Pre-acquisition scoring is a prioritization mechanism, not a cost-control shortcut: a Gate A false negative can permanently remove decisive evidence from the reachable evidence universe.

For bounded research, Gate A should usually prioritize recall over precision — important uncertain candidates may be deferred or fetched rather than permanently rejected. The pre-acquisition estimate remains a prioritization estimate, not a finding about acquired content.

| Signal | Role |
| --- | --- |
| Query/context fit | Estimate topical and task fit from title, snippet, URL, metadata, and available context. |
| Expected evidentiary value | Estimate whether the candidate is likely to contain material evidence, not merely topical language. |
| Source/provenance cues | Use publisher, author, domain, date, and source type as contextual cues, not proof of authority or bias. |
| Novelty / redundancy | Prefer candidates likely to add new evidence or independent corroboration. |
| Coverage contribution | Estimate which open Evidence Requirement the candidate may satisfy. |
| Acquisition cost/risk | Account for fetch cost, parsing difficulty, duplication, malformed content, and obvious unusability. |
| Uncertainty | Preserve how little is known before acquisition and avoid converting uncertainty into rejection. |

## Critical appraisal layer

VERA separates source appraisal, data quality, evidentiary quality, applicability, and inferential support. No single source score is permitted to silently substitute for these dimensions.

| Construct | Representative components | Rule |
| --- | --- | --- |
| Source/process appraisal | publisher/author identity, creation process, methodology visibility, funding/conflict cues, correction/retraction status when applicable | Authority is contextual and process-dependent; source reputation is not claim truth. |
| Data quality | accuracy, completeness, consistency, timeliness, interpretability, accessibility where relevant | Data quality is task-dependent and distinct from evidentiary force. |
| Evidentiary quality | methodological adequacy, directness, measurement validity, precision, replication/corroboration | Assess the evidence supporting the proposition, not only the document containing it. |
| Applicability | population/context fit, temporal fit, scope fit, transferability | High-quality evidence can be inapplicable to the active question. |
| Independence | common dataset, common study, copied reporting, citation lineage, direct replication | Multiple publications do not automatically equal independent evidence. |
| Uncertainty | epistemic, semantic ambiguity, measurement, model/evaluator, missingness | Unknown, unreported, unevaluated, and neutral are distinct states. |

> Governing separation: source credibility ≠ data quality ≠ claim quality ≠ task applicability ≠ inferential validity.

## Lateral source verification

For consequential or unfamiliar sources, VERA may leave the source and seek independent information about the author, publisher, primary-source relationship, citation lineage, corrections, and external characterization. The result is registered as evidence about the source, not as an intrinsic credibility label.

| Trigger | Possible verification action |
| --- | --- |
| Unfamiliar publisher or author | Seek independent descriptions, organizational records, or primary-source identity. |
| Consequential claim | Locate the cited original study, dataset, filing, standard, court decision, or other primary artifact where feasible. |
| Apparent consensus | Trace whether multiple reports depend on the same underlying source. |
| Conflicting source descriptions | Preserve disagreement and uncertainty rather than choosing by reputation alone. |
| Correction/retraction-sensitive domain | Check for corrections, retractions, superseding versions, or authoritative updates where feasible. |

## Semantic evidence unit and evidence relations

VERA represents evidence as machine-addressable textual units linked to exact source versions, locations, propositions, research context, and provenance.

Evidence units are the smallest capstone-visible textual evaluands. VERA adds explicit relationships among them so that the system can distinguish independent support from duplication, contradiction, qualification, and derivation.

VERA records explicit relationships among evidence and propositions, together with the evaluation method, provenance, and uncertainty state.

| Relation type | Meaning |
| --- | --- |
| supports | Evidence increases warrant for a proposition under the registered context. |
| refutes | Evidence decreases warrant for a proposition. |
| qualifies | Evidence narrows, conditions, or limits a proposition. |
| replicates | Evidence independently repeats a relevant observation or result. |
| derives-from | Evidence/report depends on another source, dataset, study, or transformation. |
| duplicates | Evidence substantially repeats the same underlying informational contribution. |
| contextualizes | Evidence changes interpretation without directly supporting or refuting the proposition. |

## Epistemic qualification

| Structure | Components | Rule |
| --- | --- | --- |
| Charge | support, refutation, uncommitted | Normalize only within a registered proposition-state frame. |
| Weight vector | source/process reliability, methodological quality, applicability, temporal validity, independence, provenance completeness | Preserve components and derivation; do not collapse into an unexplained intrinsic source score. |
| Uncertainty vector | epistemic, semantic, measurement, evaluator/model, missingness | Unknown is distinct from zero, neutrality, and absence. |
| Directness | direct evidence vs inferential/secondary distance | Do not allow proximity to a source to substitute for evidence quality, or vice versa. |
| Coverage contribution | which Evidence Requirement is addressed and to what extent | Relevance to one requirement does not imply adequacy for the question as a whole. |

## Atomic bias intersection and refusal contract

Bias is reference-relative and is not inferred from source affiliation or viewpoint. Each atomic bias assessment addresses one target under an explicit reference-relative contract. Missing, unevaluated, unsupported, or incomparable states are never treated as neutral or encoded as zero.

| Criterion | Question | Reference example |
| --- | --- | --- |
| Selection | Was relevant evidence included or omitted? | Declared candidate/evidence universe |
| Evidentiary weighting | Was consideration disproportionate to evidence quality and applicability? | Registered quality/applicability basis |
| Framing | Did wording systematically alter treatment of the target? | Counterfactual or comparison framing |
| Attribution | Was agency, cause, or responsibility assigned disproportionately? | Registered causal/evidentiary comparison |

> A bias finding requires target, criterion, reference, context, method, evidence, and provenance. Otherwise the system returns an explicit unsupported, insufficient, incomparable, or not-applicable status.

## Two-axis meta-drift

VERA evaluates **scope displacement** separately from **contextual relevance** so that useful expansion, appropriate narrowing, and genuine irrelevance are not conflated.

Scope displacement is not itself a penalty. Relevant expansion may be valuable; relevant contraction may be precise but incomplete. These dimensions can be evaluated where scope and relevance materially affect evidence selection, reasoning, or answer quality.

## Argument and inference layer

Admitted evidence does not automatically warrant a conclusion. VERA inserts an explicit argument layer between evidence and final synthesis so that the model must preserve the inferential bridge from evidence to claim and expose material alternatives.

VERA explicitly associates consequential claims with supporting and contradicting evidence, inferential warrants, assumptions, qualifications, alternatives, uncertainty, and provenance.

| Component | Requirement |
| --- | --- |
| Claim | A bounded proposition the answer may assert. |
| Supporting evidence | Exact admitted evidence supporting the claim. |
| Contradicting evidence | Material admitted evidence that weakens or conflicts with the claim. |
| Inference / warrant | The explicit reason the evidence supports the claim. |
| Assumptions | Unproven conditions required for the inference to hold. |
| Qualifier | Scope, probability, conditionality, or uncertainty appropriate to the evidence. |
| Alternatives | Plausible competing interpretations or hypotheses. |
| Discriminating evidence | Evidence that would distinguish among material alternatives where available. |

> A reputable source does not make a proposition true, and a large number of dependent sources does not create independent corroboration.

## Gate C: evidence-set adequacy

Gate C evaluates the admitted evidence collection as a body rather than treating atomic admissibility as sufficient. It prevents synthesis from beginning merely because some good evidence exists.

| Dimension | Gate C question |
| --- | --- |
| Coverage | Are all material Evidence Requirements represented? |
| Directness | Does the evidence actually address the governing question and claims? |
| Independence | Are apparent corroborations independent or derived from common sources? |
| Contradiction | Have material competing findings and interpretations been surfaced? |
| Source/evidence diversity | Are relevant evidence classes represented rather than one convenient source class dominating? |
| Currency | Is temporal coverage appropriate to the question? |
| Precision | Is the evidence precise enough to support the intended level of conclusion? |
| Missingness | Is important evidence known or plausibly likely to be absent? |
| Uncertainty | Would unresolved uncertainty materially change the answer? |
| Saturation | Is further search producing diminishing informational return relative to cost and time? |

Gate C output = `synthesize` / `search-again` / `answer-qualified` / `insufficient-evidence`. "Search-again" creates a new search iteration tied to the unmet evidence requirement rather than issuing an unconstrained generic search.

## Context-construction policy

The final context is an engineered reasoning package, not a bag of retrieved chunks. It preserves what the generator needs to reason accurately while making provenance and qualification machine-inspectable.

| Context component | Included material |
| --- | --- |
| Question frame | Governing question, scope, temporal boundary, and response requirements. |
| Evidence requirements | Satisfied, partial, contradictory, unresolved, and unavailable requirements. |
| Arguments | Claims, supporting/refuting evidence, warrants, assumptions, alternatives, qualifiers. |
| Evidence excerpts | Only admitted/qualified evidence with exact source spans and provenance IDs. |
| Source/process notes | Only appraisal information material to interpreting consequential evidence. |
| Uncertainty | Relevant uncertainty and missingness attached to claims rather than one global confidence score. |
| Counterevidence | Material conflicting findings retained explicitly to prevent one-sided synthesis. |
| Meta-drift constraints | Scope-congruence and relevance information used to prevent contraction, expansion, and irrelevance in the answer. |

## Deliberate synthesis and critical self-regulation

VERA treats the first generated answer as a draft evaluand rather than the endpoint. The system performs one bounded critique-and-revision pass when material defects are detected. This operationalizes critical-thinking self-regulation without creating an open-ended self-reflection loop.

| Answer-quality dimension | Evaluation question |
| --- | --- |
| Question coverage | Did the draft answer every material part of the governing question? |
| Claim support | Does every consequential factual claim map to admitted evidence? |
| Inferential validity | Do conclusions actually follow from the cited evidence and registered assumptions? |
| Evidence completeness | Were material admitted findings or requirements omitted from synthesis? |
| Contradiction handling | Were important conflicting findings and alternative interpretations addressed? |
| Qualification | Does language match evidence strength, applicability, and uncertainty? |
| Scope fidelity | Did the answer contract or expand beyond the governing context improperly? |
| Relevance | Is each major section materially useful to the question? |
| Synthesis | Does the response integrate evidence and explain relationships rather than concatenate summaries? |
| Clarity | Can a reader understand the conclusion, reasons, uncertainty, and limitations? |

If no material defect is detected, preserve the draft as final. If defects are material and correctable from existing evidence, create a revision with provenance to the draft and critique. If the defect is missing evidence, return to Gate C / search rather than hallucinating a repair.

## Canonical registry

VERA uses a canonical registry to preserve immutable provenance and the relationships required to reconstruct consequential research and reasoning decisions. Publicly documented record families are:

| Record family | Public purpose |
| --- | --- |
| Research and search | Governing questions, evidence requirements, search iterations, and candidate decisions. |
| Sources and provenance | Canonical source identity, acquired versions, retrieval history, and immutable provenance. |
| Evidence and appraisal | Exact evidence locations, critical-appraisal results, uncertainty, and integrity findings where applicable. |
| Evidence relationships and reasoning | Support, contradiction, qualification, derivation, claims, assumptions, alternatives, and inferential relationships. |
| Context decisions | Acquisition, admission, qualification, rejection, adequacy, and related decision rationale. |
| Answers and evaluations | Draft/final answers, consequential claims, evidence links, baseline responses, and quality evaluations. |

The implementation preserves lineage across these families so that consequential answer claims and evidence decisions can be traced backward to their supporting records without exposing the internal database schema in this public overview.

## Feedback and back-propagation

VERA preserves validated historical observations about search, appraisal, evidence decisions, reasoning, and answer quality. These derived records may inform subsequent prioritization and evaluation, but they never override current-run evidence, substitute for current uncertainty, or rewrite historical provenance.

## Agent and tool boundary

| Capability | Approach | Capstone responsibility |
| --- | --- | --- |
| Search | Reuse tool/API | Plan queries, discover candidates, register provenance, maintain search iterations. |
| Fetch/extract | Reuse | Selective acquisition into quarantine and source versioning. |
| Deterministic integrity | Build small scripts | Inspect synthetic poison/injection patterns and exact spans. |
| Segmentation | Simple implementation/library | Create evidence units with exact source spans. |
| Critical appraisal | Build bounded evaluators/rubrics | Evaluate source process, data/evidence quality, applicability, uncertainty, lineage, and directness. |
| Lateral verification | Reuse search + bounded policy | Verify consequential source claims using external evidence. |
| Meta-drift | Build bounded evaluator | Store scope displacement and relevance separately. |
| Bias/epistemic | Build | Apply reference contract and explicit charge/weight/uncertainty. |
| Argument construction | Build | Link claims, support, refutation, assumptions, alternatives, and qualifiers. |
| Adequacy Gate C | Build | Decide whether the evidence set is sufficient or search must continue. |
| Registry | Build | Canonical provenance, decisions, findings, reasoning links, feedback, and memory. |
| Context construction | Build | Create inspectable reasoning context rather than unstructured retrieval bundle. |
| Model inference | Reuse frontier model | Generate from engineered context under a fixed synthesis contract. |
| Answer critique/revision | Build bounded evaluator + one revision | Measure and remediate material answer defects. |
| Evaluation | Build cases/harness | Measure retrieval, appraisal, grounding, provenance, inference, adequacy, drift, answer quality, and comparative lift. |

## Course session mapping

| Course layer | Increment | Definition of done |
| --- | --- | --- |
| Pre-course | FastAPI skeleton, `/health`, GitHub, environment | Service runs locally and project is ready. |
| Session 1 — Foundations | Reliable `POST /ask`, structured outputs, question interpretation, Evidence Requirements Map, explicit statuses | Question, evidence requirements, and bounded candidate assessment return validated JSON. |
| Session 2 — RAG | Search/retrieval, selective acquisition, provenance, citations, evidence lineage | System distinguishes candidate, acquired, admitted, and reasoning context and can trace evidence to exact source spans. |
| Session 3 — Agents | Search, fetch, registry, integrity, appraisal, lateral verification, Gate B, Gate C tools | Agent autonomously completes the bounded inquiry loop and can search again when evidence is inadequate. |
| Session 4 — TRACE evals | Curated cases for retrieval, integrity, provenance, appraisal, bias refusal, drift, inference, grounding, answer quality, comparative lift | Baseline and improved policies are compared with observable dimension-level metrics. |
| Session 5 — Memory | Persistent source, lineage, decision, argument, answer-evaluation, and derived-stat records | Prior validated history informs later runs without overriding current evidence. |
| Production / Demo | Deployed service + compact UI + baseline comparison | End-to-end workflow and measurable quality lift are understandable in about three minutes. |

## `POST /ask` contract

The public service contract exposes the research answer together with enough evidence, decision, citation, evaluation, and status information to make the result inspectable without exposing VERA's complete internal record topology.

```json
{
  "answer": "...",
  "citations": [],
  "evidence": [],
  "decisions": [],
  "evaluation": {},
  "status": "supported"
}
```

Detailed provenance, uncertainty, reasoning, and evaluation records remain available to the system's audit layer. A generic scalar confidence field is not the governing contract; dimension-level quality and uncertainty remain inspectable.

## TRACE-oriented and comparative evaluation

| Test family | Failure example | Observable |
| --- | --- | --- |
| Evidence requirements | Material aspect of question never represented in research plan | Requirement coverage and missed-requirement rate |
| Candidate selection | High-value candidate discarded before fetch | Recall/precision on curated candidate sets; Gate A false-negative rate |
| Integrity | Synthetic poison/injection span missed or benign text falsely flagged | Detection precision/recall on synthetic corpus |
| Source/process appraisal | Source reputation substituted for methodological evidence | Rubric agreement and unsupported-appraisal refusal |
| Lineage/independence | Ten derivative reports counted as ten independent confirmations | Lineage correctness / independence-group agreement |
| Grounding | Answer contains consequential claims unsupported by admitted evidence | Claim-to-evidence support completeness |
| Provenance | Evidence cannot be traced to source version and exact span | Trace completeness |
| Bias contract | Bias declared without target/reference/criterion | Unsupported-bias refusal rate |
| Meta-drift | Relevant expansion treated as irrelevant or drift admitted as direct evidence | Coordinate/classification agreement |
| Gate C adequacy | System synthesizes despite missing material evidence requirement | Adequacy decision agreement; search-again correctness |
| Inference | Conclusion does not follow from evidence or ignores material alternative | Argument/warrant evaluation agreement |
| Answer quality | Capstone answer is inferior to direct frontier-model baseline | Dimension-level blinded preference/lift |
| Revision | Critique worsens answer or hides unresolved evidence gap | Before/after dimension changes and regression rate |
| Memory | Historical summary silently overrides contradictory current evidence | Memory precedence correctness |

## Comparative frontier-model evaluation

The capstone isolates the value of context engineering by holding the research question and, where feasible, the final synthesis model constant. A strong design compares a direct response `M(Q)` with the same model operating over engineered context `M(Q, C*)`. Additional leading models may be included as external direct baselines.

For each evaluation question `i`: `ΔQ_i = Quality(R_capstone,i) - Quality(R_direct,i)`. Preserve the distribution of dimension-level differences rather than relying only on one aggregate score.

| Quality dimension | Minimum comparison |
| --- | --- |
| Correctness | Are factual and inferential conclusions accurate relative to the available evidence? |
| Completeness | Does the answer address all material aspects of the governing question? |
| Relevance | Does the response focus on information that materially serves the question? |
| Grounding | Are consequential claims supported by traceable evidence? |
| Synthesis | Does it integrate and reconcile evidence rather than list summaries? |
| Counterevidence | Does it surface and appropriately resolve or retain material contradiction? |
| Uncertainty | Does qualification match evidence strength and unresolved missingness? |
| Clarity | Is the reasoning understandable without sacrificing material nuance? |

"Significantly superior" is a measured outcome target, not an architectural assumption. One Demo Day example can demonstrate capability; repeatable superiority requires a multi-question evaluation set and a predefined judging method.

## Demo Day script

- Enter one bounded research question and show its Evidence Requirements Map.
- Show candidate sources and Gate A priority decisions, including at least one uncertain candidate retained to protect recall.
- Fetch selected candidates into quarantine and register hashes/provenance.
- Run deterministic integrity checks, including one synthetic offending example.
- Show critical appraisal and at least one lateral verification or evidence-lineage relationship.
- Show Gate B evidence decisions and the resulting support/refute/qualify relationships.
- Show Gate C evidence-set adequacy. Ideally demonstrate one unmet requirement triggering a targeted second search iteration.
- Construct the reasoning context and generate the draft answer.
- Show critical answer evaluation and one bounded revision if materially warranted.
- Present the final grounded response beside direct responses from the selected leading-model baselines.
- Open the audit view and trace one consequential answer claim backward through argument, evidence, exact source span, source version, and method.

The observer should be able to answer four questions: What evidence did the agent seek and choose? Why did it choose or reject it? How did the evidence warrant the final conclusions? Did the engineered system produce a materially better answer than the direct-model baselines?

## MVP, stretch, and deferred scope

The full design is the architectural envelope. **Addendum A is authoritative for the October 12 MVP implementation boundary.** The MVP retains only the capabilities required to test whether engineered evidence context improves final response quality or is necessary to make that improvement auditable.

Capabilities such as richer bias analysis, full meta-drift implementation, generalized evidence-independence graphs, broader integrity detection, extensive feedback analytics, multimodal ingestion, and distributed orchestration remain stretch or deferred work unless empirical testing demonstrates that one is necessary to the MVP value test.

## Acceptance criteria

- One capstone one-liner describes the implemented text evidence-and-reasoning system.
- `GET /health` and `POST /ask` operate through FastAPI with validated structured outputs.
- Each research question produces explicit evidence requirements before retrieval.
- Search candidates are prioritized before acquisition, with uncertainty preserved and Gate A tuned to avoid premature exclusion of plausible high-value evidence.
- Selected content is staged, hashed, and registered before semantic admission.
- At least one deterministic content-integrity tool is invoked by the agent.
- Semantic evidence is traceable to exact source version and span.
- Source/process appraisal, data/evidence quality, applicability, independence, uncertainty, bias, and integrity remain separable canonical signals.
- At least one consequential source can be laterally verified or traced to an underlying primary/derivative evidence lineage.
- Scope displacement and contextual relevance remain separate measurements.
- Bias is not reported without an explicit reference-relative contract.
- Gate B context decisions are auditable and include at least admit, qualify, and reject; quarantine/excision is demonstrated with synthetic content if implemented.
- Gate C evaluates evidence-set adequacy and can trigger a targeted search-again iteration.
- Material conclusions link through explicit argument relations to supporting and contradicting evidence, assumptions, qualifiers, and alternatives where applicable.
- The first generated answer is evaluated on predefined critical-quality dimensions; one bounded revision occurs only when warranted.
- Every consequential answer claim can be traced to evidence, source version, provenance, and evaluation method.
- Comparative evaluation includes direct responses from at least one frontier baseline and measures dimension-level response-quality lift.
- The capstone is not considered successful merely because it is grounded and auditable; the final answer must demonstrate material incremental quality relative to the baseline for the Demo Day question.
- Persistent records support cross-session memory and derived feedback without replacing current-run evidence.
- The live system and UI demonstrate the principal workflow in approximately three minutes.

## Governing invariants

- **Evidence invariant:** One semantic datum, one target, one proposition or criterion, one context, one method, and one temporal scope per atomic assessment. A bias assessment additionally requires one explicit reference.
- **Context invariant:** No acquired content becomes model context merely because it was retrieved. Retrieval creates candidates. Inspection and appraisal create evidence. Argument construction creates reasoning structure. Policy creates context.
- **Adequacy invariant:** The existence of admissible evidence does not imply that the evidence set is sufficient. Final synthesis requires demonstrated coverage of material evidence requirements or an explicit qualified or insufficient-evidence status.
- **Reasoning invariant:** No consequential conclusion is warranted merely because supporting evidence was admitted. The conclusion must preserve an explicit inferential path, address material counterevidence and alternatives where present, and retain uncertainty arising from evidence, method, inference, and missingness.
- **Provenance invariant:** Original acquired content is immutable. Excision, transformation, aggregation, appraisal, validation, argument construction, answer critique, and revision create derived records linked to their parents.
- **Feedback invariant:** Historical source, method, and evaluator statistics may inform later prioritization but never substitute for current-run evidence, coverage, method, or uncertainty.
- **Resource invariant:** Every consumed resource — model/API calls, tokens, compute, wall-clock latency, and cross-instance or cross-process state — is finite and propagates or settles at a bounded, nonzero rate; no component may assume free, instant, or unbounded access to any of them. No component may consume a costed or rate-limited resource beyond what is strictly necessary to produce its required result, and no control's correctness may silently depend on unbounded consumption or instantaneous shared state across instances. Where bounded consumption or true cross-instance consistency cannot yet be guaranteed, the limitation is stated explicitly rather than presented as resolved.
- **Value invariant:** Grounding and auditability are necessary constraints, not substitutes for response quality. If the engineered pipeline adds material cost and complexity but produces a response no better than the direct leading-model baseline, it has not demonstrated sufficient incremental value for that task.

## Public disclosure boundary

This public overview documents VERA's evidence acquisition, critical appraisal, provenance, evidence-selection, reasoning-context, synthesis, and evaluation architecture at the level needed to understand and evaluate the capstone.

## Research references

1. Facione, P. A. (2023 update). *Critical Thinking: What It Is and Why It Counts.* Insight Assessment. <https://insightassessment.com/iaresource/critical-thinking-what-it-is-and-why-it-counts/>
2. Association of College and Research Libraries. (2016). *Framework for Information Literacy for Higher Education.* <https://www.ala.org/acrl/standards/ilframework>
3. Lefebvre, C., Glanville, J., Briscoe, S., et al. (2025). *Chapter 4: Searching for and selecting studies.* Cochrane Handbook for Systematic Reviews of Interventions, version 6.5.1. <https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-04>
4. Wang, R. Y., & Strong, D. M. (1996). *Beyond Accuracy: What Data Quality Means to Data Consumers.* Journal of Management Information Systems, 12(4), 5–33. <https://doi.org/10.1080/07421222.1996.11518099>
5. Critical Appraisal Skills Programme. (2026). *What is critical appraisal?* <https://casp-uk.net/what-is-critical-appraisal/>
6. Cochrane/GRADE. *Chapter 14: Completing Summary of Findings tables and grading the certainty of the evidence;* GRADE Working Group materials. <https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-14>
7. Wineburg, S., & McGrew, S. (2019). *Lateral Reading and the Nature of Expertise: Reading Less and Learning More When Evaluating Digital Information.* Teachers College Record, 121(11). <https://doi.org/10.1177/016146811912101102>
8. Sperber, D., Clément, F., Heintz, C., Mascaro, O., Mercier, H., Origgi, G., & Wilson, D. (2010). *Epistemic Vigilance.* Mind & Language, 25(4), 359–393. <https://doi.org/10.1111/j.1468-0017.2010.01394.x>
9. PRISMA. (2020). *PRISMA 2020 flow diagram and checklist.* <https://www.prisma-statement.org/prisma-2020-flow-diagram>
10. Facione, P. A., & Facione, N. C. *Holistic Critical Thinking Scoring Rubric.* Insight Assessment. <https://insightassessment.com/iaresource/the-holistic-critical-thinking-scoring-rubric/>

> **Transfer note:** VERA imports transferable principles from systematic-review, evidence-based practice, information-literacy, argumentation, and data-quality research. It does not claim PRISMA, GRADE, CASP, or Cochrane compliance for general web research.

---

# Addendum A — October 12 MVP and delivery milestones

## Purpose and governing constraint

This addendum converts the full architecture into the minimum vertical slice required to test the capstone thesis before **12 October 2026**. The full design remains the governing envelope. The MVP is not a miniature implementation of every capability in the full design. It is the smallest end-to-end system capable of testing whether deliberate, auditable evidence acquisition, critical evaluation, and context construction can cause a frontier model to produce a materially better research response than the same model produces directly.

**MVP proposition:** For a bounded research question, an engineered evidence context can produce a measurably better grounded response than a direct leading-LLM baseline, while preserving an inspectable chain from consequential evidence decisions to source, evidence, provenance, and evaluation method.

**MVP decision rule:** A capability is on the October 12 critical path only if it materially increases the probability of improving final response quality or is necessary to make that improvement auditable.

## A.1 Minimum end-to-end workflow

```
Question → Evidence Requirements → Search → Gate A → Fetch/Provenance → Evidence Appraisal
        → Gate B → Gate C → Context Construction → Draft Answer → Critique/Revision
        → Final Answer → Baseline Comparison
```

The three decision gates are deliberately simplified for the MVP:

| Gate | MVP question | Minimum outputs |
| --- | --- | --- |
| Gate A — acquisition | Is this candidate sufficiently plausible and useful to justify acquisition? | `fetch` / `defer` / `reject` |
| Gate B — admission | After acquisition and appraisal, may this evidence inform reasoning context? | `admit` / `qualify` / `reject` |
| Gate C — adequacy | Does the admitted evidence set adequately cover the material requirements of the research question? | `adequate` / `search_again` / `insufficient` |

## A.2 MVP required capabilities

| Capability | MVP definition of done |
| --- | --- |
| Service contract | `GET /health` and validated `POST /ask` through FastAPI. |
| Evidence requirements | Create a small, explicit map of the material findings or subquestions needed to answer the bounded research question. |
| Candidate discovery | Search the web and register candidate title, URL, snippet/rank, query/run, and Gate A decision. |
| Selective acquisition | Fetch selected textual content, stage it, compute a content hash, and preserve retrieval provenance. |
| Semantic evidence | Extract machine-addressable evidence spans tied to the exact source version. |
| Critical appraisal | Evaluate each consequential evidence unit with a fixed, inspectable rubric. Minimum dimensions: relevance, source/process quality, claim support, applicability, uncertainty, and support/challenge relation. |
| Context decisions | Apply Gate B and retain the decision, rationale, contributing evidence, method/rubric version, and provenance. |
| Evidence-set adequacy | Apply a bounded Gate C coverage check. Permit at most one search-again iteration in the first MVP. |
| Reasoning context | Organize admitted/qualified evidence into a compact context that exposes support, contradiction, uncertainty, and source lineage without dumping the registry into the model prompt. |
| Grounded synthesis | Generate a cited draft answer using only the permitted reasoning context. |
| Answer critique | Evaluate the draft for correctness, completeness, grounding, synthesis, relevance, clarity, and material uncertainty. Permit one bounded revision when a material defect is detected. |
| Baseline comparison | Ask the same final model the same research question directly, without the engineered evidence context, and preserve that response as the primary control. |
| Comparative evaluation | Evaluate direct and engineered responses with a predefined rubric and preserve dimension-level results and evaluator rationale. |
| Audit view | Expose enough of the trace that an observer can determine what evidence was selected, what was rejected or qualified, why, and where each consequential decision originated. |

## A.3 Minimum canonical data model

The MVP uses the same public record families described above, implemented only to the depth necessary for the October 12 value test. At minimum it must preserve:

- the governing research question and evidence requirements;
- candidate discovery and acquisition decisions;
- immutable source/version provenance;
- exact evidence locations and critical-appraisal results;
- context/admission and evidence-set adequacy decisions;
- direct-baseline and engineered answers;
- consequential claim-to-evidence traceability; and
- dimension-level comparative evaluation results.

The implementation may use a compact schema, but it must preserve provenance, uncertainty, missingness, and immutable source lineage.

## A.4 MVP evaluation contract

The MVP must evaluate outcome quality as well as process integrity. Grounding and auditability do not compensate for an inferior final response.

| Dimension | MVP question |
| --- | --- |
| Correctness | Are consequential factual and analytical claims accurate relative to the available evidence? |
| Completeness | Does the response address every material part of the bounded research question? |
| Grounding | Are consequential claims supported by admitted or qualified evidence? |
| Synthesis | Does the response integrate evidence and reconcile material relationships rather than concatenate summaries? |
| Relevance | Does the response remain useful and responsive to the governing question? |
| Clarity | Is the reasoning and resulting conclusion understandable and appropriately organized? |
| Uncertainty | Are material evidentiary limitations, contradictions, and unresolved uncertainty represented appropriately? |
| Trace completeness | Can consequential evidence and answer decisions be traced to source/version/span, provenance, and evaluation method? |

**Primary comparative design:** where feasible, hold the final generator constant. Compare `M(Q)`, the model answering the research question directly, against `M(Q, C*)`, the same model answering with the MVP-selected reasoning context. This isolates the incremental value of the context-engineering pipeline more cleanly than comparing different generators.

## A.5 MVP acceptance criteria

1. One bounded research question completes the full MVP workflow without manual database intervention.
2. At least one candidate is evaluated before acquisition and every acquired source is versioned and provenance-linked.
3. Every consequential evidence unit used in the final answer is traceable to an exact source version and span.
4. Gate B demonstrates at least admit and qualify/reject actions with inspectable rationale.
5. Gate C explicitly returns `adequate`, `search_again`, or `insufficient`; at least one curated test demonstrates the search-again or insufficient path.
6. The final model receives a compact engineered reasoning context rather than an undifferentiated registry dump.
7. The first generated response is evaluated as a draft; one bounded revision is supported when material deficiencies are found.
8. The same research question is run as a direct leading-model baseline and retained for comparison.
9. Direct and engineered responses are compared on predefined quality dimensions rather than only an opaque scalar score.
10. The Demo Day case shows a materially superior engineered response. If it does not, the MVP records the result as a failed value test rather than redefining success.
11. An observer can answer: What evidence was chosen? What was rejected or qualified? Why? Can each consequential decision be traced to its source, evidence, provenance, and evaluation method?
12. The complete demonstration remains understandable in approximately three minutes.

## A.6 Explicitly deferred from the October 12 MVP

The following remain part of the full design but are not required to establish the first value test:

- Generalized or exhaustive bias taxonomy beyond the minimum appraisal needed by the selected research domain.
- Full two-axis meta-drift implementation and distribution-preserving drift summaries.
- Multiple content-integrity detectors, generalized poison/trojan detection, autonomous remediation, and production malware analysis.
- Bounded excision workflow beyond a synthetic demonstration, if any.
- Full lateral-verification automation and retraction/correction infrastructure.
- General evidence-independence graph beyond a simple shared-origin or derivation flag.
- Multiple evaluator-model agreement, adaptive evaluator calibration, and complex source-history scoring.
- Derived source dashboards, generalized feedback analytics, and broad cross-run reputation models.
- Multimodal ingestion, universal ontology architecture, adaptive semantic geometry, and distributed orchestration.

## A.7 Delivery milestones to 12 October 2026

Milestones are outcome gates rather than promises to implement every subsystem in the full design. A milestone is complete only when its artifact works end to end at the stated boundary.

| Milestone | Target | Deliverable | Exit criterion |
| --- | --- | --- | --- |
| M0 — Scope freeze | 9 Sep | Freeze the full design as the envelope and this addendum as the MVP boundary. Select the first bounded research question and baseline model. | No new feature enters MVP unless it improves response quality or auditability. |
| M1 — Service and records | 10–13 Sep | Working `/health` and `/ask`; validated schemas; minimal persistent records for question/run/candidate/source. | One request persists and returns structured output with stable IDs. |
| M2 — Search and provenance | 14–19 Sep | Search, Gate A, selective fetch, staging/hash, source/version provenance. | A question produces registered candidates and acquired immutable source versions. |
| M3 — Evidence and Gate B | 20–25 Sep | Evidence extraction, fixed critical-appraisal rubric, admit/qualify/reject decisions. | Every admitted/qualified evidence span has a source/version/span, assessment, rationale, method, and provenance. |
| M4 — Gate C and context | 26 Sep–1 Oct | Evidence-requirements coverage, bounded adequacy check, one search-again loop, compact reasoning-context construction. | System either constructs adequate context, searches once for a named gap, or returns insufficient evidence. |
| M5 — Synthesis and repair | 2–5 Oct | Grounded draft generation, claim-to-evidence links, answer critique, one bounded revision. | Final answer is cited, claim-traceable, and passes the MVP answer-quality checks or is explicitly qualified. |
| M6 — Baseline and eval | 6–8 Oct | Direct same-model baseline plus comparative evaluation harness. Curate initial evaluation cases. | For the Demo question, both conditions are stored and scored on the predefined dimensions with rationale. |
| M7 — Demo hardening | 9–10 Oct | Compact UI/audit view, deterministic demo path, latency/error handling, cached fallback artifacts where appropriate. | A three-minute rehearsal completes without hidden manual steps and exposes the evidence-decision trace. |
| M8 — Freeze and rehearse | 11–12 Oct | Code/content freeze except critical defects; repeat evaluation and Demo Day rehearsal. | Reproducible final run, preserved baseline comparison, known limitations documented, demo ready. |

## A.8 Stretch milestones after MVP stability

| Priority | Stretch milestone | Trigger |
| --- | --- | --- |
| S1 | Add bounded lateral source verification for consequential sources. | Only after M5 is stable and source credibility is a demonstrated quality bottleneck. |
| S2 | Add simple evidence-lineage/independence grouping beyond shared-origin flags. | When apparent corroboration materially affects conclusions. |
| S3 | Restore two-axis meta-drift at candidate, evidence, and answer stages. | When scope/relevance errors appear in evaluation cases. |
| S4 | Add one deterministic prompt-injection/content-integrity detector and synthetic test. | When Session 3 / tooling requirements are otherwise satisfied. |
| S5 | Expand evaluation from the Demo question to a 10–20 question blinded or model-independent comparison set. | After the end-to-end pipeline is stable. |
| S6 | Add persistent derived source/method feedback for Session 5 memory. | After current-run evidence precedence and provenance are verified. |
| S7 | Optimize latency, token use, model routing, and acquisition cost. | After quality lift is demonstrated; optimization must not erase the measured advantage. |

## A.9 Stop/go rules

- If a proposed feature does not improve answer quality, evidence adequacy, or traceability, defer it.
- If Gate A reduces recall on high-value evidence, loosen Gate A before adding more scoring complexity.
- If Gate C repeatedly declares adequacy despite obvious missing evidence, repair evidence requirements and coverage logic before adding downstream sophistication.
- If the final response is worse than the direct baseline, inspect evidence coverage, context construction, and synthesis before adding provenance or bias features.
- If the same-model engineered-context condition does not show material lift on the Demo question by M6, narrow or change the research question only if the new question remains a legitimate instance of the declared capstone domain. Record the failed case rather than discard it.
- Once the MVP demonstrates material quality lift and complete traceability, freeze the critical path. Stretch work must not jeopardize the October 12 demonstrable system.

## A.10 Relationship to the full design

This addendum does not supersede the full design. It defines the implementation boundary for the capstone MVP. The full design continues to govern conceptual semantics, provenance invariants, evidence and reasoning distinctions, and post-MVP evolution. Where this addendum simplifies a construct, the simplification is an implementation deferral rather than a conceptual redefinition.
