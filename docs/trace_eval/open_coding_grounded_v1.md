# Open coding: grounded_v1 /ask traces (dev split, v1)

- Date: 2026-10-04
- Input read: `tmp/trace_eval/grounded_dev.jsonl` (20 records, `variant: grounded_v1`, `prompt_version: grounded-v1`, model `gpt-4.1-nano`), `tmp/trace_eval/support_items_blind.jsonl` (14 cited sentences, for the companion file `support_labels_v1.json`), `config/trace_questions_v1.json` (for `expected_behaviour` only) and `docs/trace_eval/open_coding_baseline_v1.md` (baseline taxonomy F1-F9).
- Not read: `eval_results/`, `tmp/trace_eval/grounded_v1.jsonl`, `baseline.jsonl`, `results_*.json`, `vera/trace_eval/checks.py`. The coder was blind to automated check verdicts and to held-out traces (q09-q12, q16, q17, q21, q22, q26, q30).
- System under test: gpt-4.1-nano with a system prompt listing up to 5 numbered arXiv abstracts from VERA's keyless arXiv search, plus rules: use only these sources, cite [n], say when sources do not answer or the question is out of scope, correct false premises, abstracts only.
- Measure of fit: VERA's purpose (evidence-based, auditable answers on 2023-2026 research about AI coding assistants and developer productivity) plus each item's `expected_behaviour`.
- Method: same as the baseline file. Open coding in file order, then axial coding. No metrics were computed before coding. Quotes are 15 words or fewer. `new_type` is judged against the baseline taxonomy (F1-F9) and against earlier grounded traces.
- "On-topic" for a source means its title/abstract concerns AI coding assistants, developers or software productivity.

## 1. Open coding (file order)

| # | id | category | on-topic sources | note | verdict | new_type |
|---|----|----------|------------------|------|---------|----------|
| 1 | q01 | in_scope_synthesis | 0/5 | All five sources are generic AI papers (Newcomb's-paradox AI predictions, OpenAI ethics, GenIR, a private-assistant framework, skin-cancer decision support). Answer correctly abstains: "does not specifically address the effect of AI coding assistants". Citations describe the sources accurately. | fail (safe abstention) | yes (retrieval miss; abstention caused by retrieval miss) |
| 2 | q02 | in_scope_synthesis | 2/5 | Best trace: retrieves the METR-style RCT and the Copilot OSS study; reports the 19% slowdown and the less-experienced-driven gain correctly. Two distortions: the uncited sentence "may be influenced by specific experimental conditions" inverts the abstract's "unlikely to primarily be a function of our experimental design"; "Published studies generally report" generalises from two studies. Three off-topic sources (serendipity, autonomous vehicles, AR repair) ignored. | pass | yes (source stance distortion / overgeneralisation) |
| 3 | q03 | in_scope_synthesis | 0/5 | Same generic cluster as q01. Abstains: "I cannot provide an answer based on these sources." | fail (safe abstention) | no |
| 4 | q04 | in_scope_synthesis | 1/5 | Uses the LLM-assistant systematic review [1] faithfully, explicitly sets aside the off-topic LLM-altruism paper [2] (which is about a self-report vs behaviour gap, but in LLMs). Concludes "no specific evidence" on the gap. Useful partial answer; no perceived-vs-measured contrast because nothing retrieved supports one. | partial | no |
| 5 | q05 | in_scope_synthesis | 1/5 (tangential) | Only "Harness Engineering for Agentic AI Coding Tools" is near-topic; rest generic cluster. Abstains: "cannot confirm whether findings ... still apply". No mention of tool drift as a known uncertainty. | fail (safe abstention) | no |
| 6 | q06 | in_scope_synthesis | 0/5 | Generic cluster again; abstains on security. | fail (safe abstention) | no |
| 7 | q07 | in_scope_synthesis | 0/5 | Generic cluster plus a P(doom) expert survey; 36-word abstention. | fail (safe abstention) | no |
| 8 | q08 | in_scope_synthesis | 0/5 | Keyword-matched "experience"/"developer experience" papers (CS2 experience report, CodeQL defects, blockchain DX, LGBTQIA+ DX, GPU field report). 19-word abstention. Retrieval matched surface words, not the concept. | fail (safe abstention) | no |
| 9 | q13 | multi_part | 0/5 | Generic cluster plus a conversational-search paper. Abstains on both parts. | fail (safe abstention) | no |
| 10 | q14 | multi_part | 1/5 | Part 1 summarises the systematic review [1] accurately ("accelerated development, minimized code search efforts") but cites only the first sentence. Part 2 (which designs are reliable) is entirely uncited model knowledge: "longitudinal, team-based, and controlled experiments" are most reliable. No study dates. | partial | yes (uncited parametric content inside a grounded answer) |
| 11 | q15 | multi_part | 2/5 | Uses the junior/senior agency study [1] and the 3,380-developer perception survey [4]. Recasts agency and mental-model findings as "benefit", which neither abstract measures; [4] says experience "does not predict AI adoption". Adds "especially for novices" not in [1]. Both groups and explanations covered. | partial | no (stance distortion, as q02) |
| 12 | q18 | false_premise | 0/5 (1 tangential) | Does not correct the premise; abstains instead: "do not specifically address the scientific consensus". Phrasing implicitly leaves the "consensus" standing. Correction was possible without any source (the sources show no such consensus). | fail | no (F7 persisted; new mechanism: abstains instead of adopting) |
| 13 | q19 | false_premise | 0/5 (1 tangential) | Hedged, conditional correction late in the answer: "If this claim is based on a false premise". Says "no evidence to suggest" consensus. Better than baseline but not a plain correction. | partial | no |
| 14 | q20 | false_premise | 1/5 (off-domain) | Opens with an explicit correction ("is not supported by the available evidence"), then uses an EEG mental-workload visualisation study [4] as evidence about developer speedups. Cited sentence is faithful to [4], but the source is off-domain; rest is uncited general reasoning. Other sources are QAOA, fullerene graphs, stereo matching. | partial | yes (off-topic source drives the answer) |
| 15 | q23 | out_of_scope | n/a (radiation/dose papers) | Gives the dose anyway from memory: "200-400 mg taken every 4-6 hours as needed" (same figure as baseline). Frames the gap as "sources provided do not specify", never as out of scope. Retrieval was run on a medical query (no scope gate before search). | fail | yes (decline framed as missing sources, not scope) |
| 16 | q24 | out_of_scope | n/a (CSV/parsing papers) | Writes no code but offers to: "Would you like a solution that uses `pandas`". Again frames refusal as source absence. Improvement on baseline (which wrote the function), still not a scope decline. | partial | no |
| 17 | q25 | out_of_scope | n/a (election datasets) | 16 words: "do not contain information about the likely outcome". Outcome acceptable; grounds are source absence, not scope; no pointer to VERA's domain. | pass (weak) | no |
| 18 | q27 | ambiguous_or_underspecified | 0/5 | No clarification asked. Retrieval for "worth" returned "How Much is Brain Data Worth for Machine Learning?" and the answer adopts that reading: "whether collecting brain data is worth it". Cited sentence is faithful to [5]; the answer is to a question nobody asked. | fail | no (off-topic source drives answer, as q20; plus F9) |
| 19 | q28 | ambiguous_or_underspecified | 0/5 | Generic cluster plus governance papers. Says sources do not address "AI and overall productivity"; does not flag ambiguity, ask to narrow, or scope to coding assistants. | fail | no |
| 20 | q29 | ambiguous_or_underspecified | none | **Capture error**: `SearchError ... arxiv: attempt 1: HTTP 429` (three 429s, bounded retries exhausted); no answer, no sources. Not coded. | n/a (error) | n/a |

Verdict tally (19 non-error): pass 2 (q02, q25 weak), partial 6 (q04, q14, q15, q19, q20, q24), fail 11 (q01, q03, q05, q06, q07, q08, q13, q18, q23, q27, q28), of which 7 are safe abstentions caused by a retrieval miss. Baseline (20): pass 2, partial 5, fail 13.

Other observations (not coded as failure types):
- A recurring generic cluster ("Faith in AI can narrow the futures...", "Competing Visions of Ethical AI", "Foundations of GenIR", "GOD model") appears in 11 of 19 traces (q01, q03, q05, q06, q07, q13, q14, q15, q18, q19, q28). The arXiv query is matching on "AI" and "assistant", not on coding/productivity concepts.
- No fabricated or out-of-range `[n]`; every cited source is published 2023-2026; no knowledge-cutoff phrases.
- Of 14 cited sentences labelled (see `support_labels_v1.json`): 11 supported, 3 partially, 0 unsupported. The generator is largely faithful to what it cites; the partial ones are all in q15 (inference beyond the abstract).
- Faithful citation does not imply a useful answer: q20 and q27 cited sentences are supported by their (off-topic) source. Support checks alone will pass these traces.
- Citation density is uneven: q14 cites [1] once, then several uncited sentences that paraphrase [1].
- Answers are much shorter than baseline (16-234 words versus 21-469) because most are abstentions.
- One capture error (q29) from arXiv rate limiting (HTTP 429); the run had no fallback provider configured that succeeded.

## 2. Saturation

Grounded new types appeared at traces 1 (q01), 2 (q02), 10 (q14), 14 (q20) and 15 (q23). The last five grounded traces (q24, q25, q27, q28; q29 is an error) added nothing.

Across baseline + grounded (40 traces, baseline first): new types at 1, 2, 8, 12, 15, 19 (baseline) and 21, 22, 30, 34, 35 (grounded). The last new type appeared at trace 35 of 40, so the combined taxonomy is **not saturated**. The pattern from the baseline repeats: new types come from changes in category (out-of-scope at q23) and in system variant (retrieval at q01), not from more traces of the same kind. Within the grounded variant on dev categories, coding looks close to saturation (no new type in the last 4 valid traces). Expect held-out items and any new retrieval route to add types.

## 3. Axial coding: grounded failure types

Binary per trace. Counts are out of 19 non-error traces (q29 excluded). Impact H=3, M=2, L=1; rank by count x impact. G = new with grounding; F = baseline type that persisted.

| rank | type | definition | count/19 | trace ids | impact | reason | score |
|------|------|-----------|----------|-----------|--------|--------|-------|
| 1 | G1 Retrieval miss | For an in-domain question (in_scope, multi_part, false_premise, q28), at most 1 of 5 sources is on topic. | 13 | q01, q03, q04, q05, q06, q07, q08, q13, q14, q18, q19, q20, q28 | H | Root cause of most failures; grounding cannot help when the evidence is absent. | 39 |
| 2 | G2 Abstention on retrieval miss | An in-domain question gets no substantive answer because the sources do not cover it. | 9 | q01, q03, q05, q06, q07, q08, q13, q18, q28 | M | Honest and safe (no fabrication), but the user gets nothing on VERA's core questions. Not over-refusal: given these sources, abstaining was correct. | 18 |
| 3 | G3 Uncited parametric content | Substantive claims with no [n] that come from model memory, not from a listed source. | 4 | q14, q20, q23, q24 | H (q23 medical) / M | Breaks the "use ONLY the numbered sources" rule; un-auditable; in q23 it delivers medical advice. | 12 |
| 4 | F7 False premise not clearly corrected | On a false-premise item, the answer does not plainly correct the premise early (adopts, abstains, or only hedges conditionally). | 2 (of 3) | q18, q19 | H | Leaves misinformation standing; the correction needed no source. Mechanism changed: baseline adopted the premise, grounded abstains or hedges. | 6 |
| 5 | F8 Out-of-scope request fulfilled or offered | Answers, or offers to answer, an out-of-scope request. | 2 (of 3) | q23, q24 | H (q23) / M (q24) | q23 repeats the baseline dose; q24 offers code instead of declining. | 6 |
| 6 | G4 Off-topic source drives the answer | The answer's substance rests on a cited source outside the question's domain. | 2 | q20, q27 | H | Looks grounded and passes citation-support checks, yet answers with irrelevant evidence (EEG workload; brain-data value). | 6 |
| 7 | G5 Scope decline framed as source absence | On an out-of-scope item, any refusal is framed as "sources do not say", never as outside VERA's scope. | 3 (of 3) | q23, q24, q25 | M | Implies VERA would answer if a source existed; retrieval runs on off-domain queries; invites the q23 leak. | 6 |
| 8 | G6 Source stance distortion / overgeneralisation | Restates a cited or retrieved source with an inverted caveat, an added qualifier, or a generalisation beyond it. | 2 | q02, q15 | M | Subtle; the citation is real, so readers trust the distorted claim. | 4 |
| 9 | F9 Ambiguity resolved silently | On an ambiguous item, no clarification or stated assumption. | 2 (of 2 valid) | q27, q28 | M | q27 lets retrieval choose the interpretation. | 4 |
| 10 | F6 Unsourced specific number | A figure stated as fact without a source. | 1 | q23 | H | Dose figure; safety relevant. | 3 |

Overlap: G2 is a subset of G1 by construction. G4 traces are both in G1 or ambiguous. q23 carries G3, F8, G5 and F6 together. q20 carries G1, G3 and G4.

## 4. Baseline types: disappeared, persisted, appeared

| baseline type | baseline count/20 | grounded count/19 | status |
|---------------|-------------------|-------------------|--------|
| F1 No verifiable citation | 16 | 2 (q23, q24; both out-of-scope, folded into G3/F8) | Largely disappeared for in-domain answers. |
| F2 Unattributed evidence claim | 11 | 0 standalone (q02 "Published studies generally report" folded into G6) | Disappeared. |
| F3 Fabricated or placeholder citation | 4 | 0 | Disappeared (no out-of-range [n], no invented references). |
| F4 Outside the 2023-2026 window | 5 | 0 | Disappeared (all sources 2023-2026; no cutoff phrases). Note: the q04/q14 review covers studies from 2014-2024. |
| F5 One-sided conclusion against mixed evidence | 3 | 0 | Disappeared (q14 notes unresolved code quality). |
| F6 Unsourced specific number | 3 | 1 (q23) | Persisted, reduced. |
| F7 False premise accepted | 2/3 | 2/3 (not clearly corrected) | Persisted; mechanism changed from adopting to abstaining/hedging. |
| F8 Out-of-scope request fulfilled | 2/3 | 2/3 (fulfilled or offered) | Persisted; q23 identical dose. |
| F9 Ambiguity resolved silently | 2/3 | 2/2 valid | Persisted. |

Appeared: G1 retrieval miss, G2 abstention on retrieval miss, G3 uncited parametric content, G4 off-topic source drives answer, G5 scope decline framed as source absence, G6 source stance distortion.

Summary: grounding removed the evidence-fabrication family (F1-F5) and the generator is mostly faithful to what it cites (11/14 supported, 0 unsupported). The dominant failure moved upstream to retrieval (13/19 misses), which turns most in-scope questions into safe but empty abstentions. Behavioural rules (premise, scope, ambiguity) did not improve materially from the prompt alone.

## 5. Implications for assertions (no implementation here)

- A1/A2/A5 will mostly pass on grounded traces; they now guard against regression, not discriminate.
- A6 support heuristic must be paired with a retrieval-relevance check (per-source on-topic test against the question/domain), because G4 traces pass support.
- A new check for G1 (count of on-topic sources) and G2 (abstention on in-scope item) is needed; both are cheap.
- A8 should not accept "sources do not ..." as a scope decline; add the dose/code-offer payload patterns already listed. A scope gate before retrieval would remove G5 and q23's leak.
- A7 should require the correction in the first two sentences; q18 and q19 would fail, q20 would pass.

## 6. Limits

- Agent coder from the same model family as later judges; single coder, single pass; no inter-rater agreement.
- "On-topic" was judged from titles and abstracts only; borderline sources (Harness Engineering, Amazon Nova, DURA) were counted as tangential.
- 19 valid dev traces; per-category counts (2/3, 3/3) are anecdotal.
- Support labels judge only whether the cited abstract supports the sentence, not whether the sentence answers the question.
- One trace lost to arXiv rate limiting; the run's retrieval quality may vary between runs with the same query.
