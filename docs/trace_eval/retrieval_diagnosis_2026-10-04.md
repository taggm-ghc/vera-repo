# Retrieval diagnosis, grounded_v1 traces (2026-10-04)

Question: is the grounded variant's retrieval failure (Week 4 TRACE, `docs/trace_eval/open_coding_grounded_v1.md`: at most 1 of 5 sources on topic in 13 of 19 dev traces) caused by the corpus, by question granularity, or by how VERA turns a question into a search query?

Finding: **mainly the question-to-query translation.** The corpus has relevant material; question granularity is a minor factor.

## 1. What the query builder sends (recorded traces, no new calls)

`vera.search_providers.build_arxiv_query` takes the first `max_terms` (8) non-stopword tokens of the question, joins them with `OR` across all fields (`all:`), and adds the 2023-2026 date range (config `search.arxiv.query`). Questions written for a reader ("What does published evidence show about ...") therefore produce queries dominated by meta-words (`published`, `evidence`, `show`, `about`, `such`, `studies`), and with `OR` any paper containing one of them qualifies. The 8-term cap can also cut the core topic (q01 loses "developer productivity").

On-topic count = source titles matching a coding/developer keyword pattern (a crude heuristic: it also counts non-coding "Copilot" products, so it overstates rather than understates). In-scope, multi-part and false-premise questions with sources:

| id | split | on-topic (title keyword) | query terms (OR, all fields) |
|---|---|---|---|
| q01 | dev | 0/5 | published evidence show about ai coding assistants effect |
| q02 | dev | 2/5 | published studies find experienced developers working familiar mature |
| q03 | dev | 0/5 | much favourable evidence ai coding assistants comes vendor-affiliated |
| q04 | dev | 2/5 | studies show about gap between developers self-reported productivity |
| q05 | dev | 1/5 | findings about older ai coding tools models still |
| q06 | dev | 0/5 | published evidence say about effect ai coding assistants |
| q07 | dev | 0/5 | results controlled experiments ai coding assistants differ field |
| q08 | dev | 3/5 | literature report about developer experience level changes benefit |
| q09 | heldout | 1/5 | outcome measures such task completion time pull request |
| q10 | heldout | 1/5 | published studies say about ai coding assistants long-term |
| q11 | heldout | 0/5 | task type such greenfield versus maintenance work moderate |
| q12 | heldout | 0/5 | limitations such sample size study duration researchers acknowledge |
| q13 | dev | 0/5 | controlled experiments show about ai coding assistant speed |
| q14 | dev | 1/5 | summarise published evidence ai assistants developer productivity then |
| q15 | dev | 2/5 | junior senior developers differ benefit ai coding assistants |
| q16 | heldout | 0/5 | field evidence exists ai assistants companies compare lab |
| q17 | heldout | 0/5 | factors moderate ai coding assistant effects evidence say |
| q18 | dev | 2/5 | given scientific consensus ai coding assistants double developer |
| q19 | dev | 1/5 | all published studies agree ai coding assistants reduce |
| q20 | dev | 0/5 | since developers self-reported speedups always match measured we |
| q21 | heldout | 1/5 | now settled ai assistants no effect experienced developers |
| q22 | heldout | 1/5 | every independent study found ai coding assistants make |

Mean on-topic: **0.82 of 5** over 22 questions. Broad questions fail as badly as narrow ones (q01, the frozen question itself: 0/5).

## 2. Does the corpus have the studies? (6 diagnostic arXiv calls, $0)

The six zero-hit questions q01, q06, q07, q11, q13, q16 were re-run with hand-focused queries: a domain core (`all:copilot OR abs:"coding assistant" OR abs:"AI pair programming" OR abs:"AI-assisted programming"`) AND the question's facet (productivity, security, randomized/field study, maintenance/task type, speed/code quality, enterprise/company), same date range. Relevant studies appeared, for example an evaluation of the code quality of AI-assisted code generation, a field report on GitHub Copilot and developer productivity, and a user-centred security evaluation of Copilot.

Caveats: the keyword count reported 4-5/5 on topic, but by eye several hits are unrelated products named "Copilot" (security, tutoring, industrial assistants), and q01 and q06 returned the same top results, so arXiv's lexical relevance ranking stays crude. The corpus is adequate for the topic; a naive query fix still lets noise through.

## 3. Granularity and corpus limits

A few questions are narrow (q11 greenfield vs maintenance, q12 acknowledged limitations) and the literature on them is sparse, so they would retrieve little even with good queries. Not checked: how much of the productivity evidence lives outside arXiv (industry reports, journals); that would cap recall regardless of the query.

## 4. Candidate fixes (not implemented; plan before code)

1. Question-to-query translation: drop meta-words, always include the domain core phrase, AND the question's facet, search abstracts (`abs:`) rather than all fields.
2. Over-fetch (15-20) then keep the 5 most on-topic before prompting.
3. Disambiguate "copilot" (exclude non-coding products).
4. Measure retrieval on its own: hand-label the top 5 for all 30 frozen questions before and after (precision@5).

Evidence files: `tmp/trace_eval/grounded_v1.jsonl` (local, gitignored); this table was regenerated from it with the committed config and query builder.

> Status (2026-10-04): the query-translation defect and the per-call rate-gate defect described here are fixed in code by p3m3 item #71 (not yet re-measured live).
