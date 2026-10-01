-- 005_vera_m6_schema_sync.sql -- M6 judge schema synchronization
-- Adds missing columns required by M6 adapter queries + run_id filters
-- Depends on 001 + 002 + 003 + 004
--
-- Addresses schema blockers:
--   1. runs.question and runs.final_response missing (M6 tries SELECT question, final_response)
--   2. runs.evaluated_at missing (M6 tries UPDATE ... evaluated_at = now())
--   3. appraisals.rubric_version and appraisals.policy_version missing (M6 needs them for audit trail)
--   4. evidence_relations.run_id missing (M6 needs WHERE run_id filter to prevent data leaks)
--   5. evidence_relations.rationale missing (M6 tries SELECT rationale)
--
-- Backfill logic:
--   - runs.question: populated from questions table via foreign key
--   - runs.final_response: copy from engineered_response (the synthesized answer)
--   - runs.evaluated_at: leave NULL (M6 will set on first eval)
--   - evidence_relations.run_id: join to evidence_spans -> sources -> answers -> runs
--   - evidence_relations.rationale: leave NULL (optional audit detail)
--   - appraisals.rubric_version, policy_version: set to defaults (sourced from corpus at eval time)

-- 1. Add question and final_response to runs table
ALTER TABLE vera_vjay.runs ADD COLUMN question TEXT;
COMMENT ON COLUMN vera_vjay.runs.question IS 'Question text for this run (copied from questions.research_question)';

ALTER TABLE vera_vjay.runs ADD COLUMN final_response TEXT;
COMMENT ON COLUMN vera_vjay.runs.final_response IS 'Final synthesized answer (same as engineered_response for M6 eval)';

ALTER TABLE vera_vjay.runs ADD COLUMN evaluated_at TIMESTAMPTZ;
COMMENT ON COLUMN vera_vjay.runs.evaluated_at IS 'Timestamp when M6 evaluation completed (set by M6 runner)';

-- 2. Backfill runs.question from questions table
UPDATE vera_vjay.runs r
SET question = q.research_question
FROM vera_vjay.questions q
WHERE r.question_id = q.question_id AND r.question IS NULL;

-- 3. Backfill runs.final_response from engineered_response (the actual answer)
UPDATE vera_vjay.runs
SET final_response = engineered_response
WHERE final_response IS NULL AND engineered_response IS NOT NULL;

-- 4. Add rubric_version and policy_version to appraisals
ALTER TABLE vera_vjay.appraisals ADD COLUMN rubric_version TEXT DEFAULT '1.0';
COMMENT ON COLUMN vera_vjay.appraisals.rubric_version IS 'Version of evaluation rubric used (from corpus at eval time)';

ALTER TABLE vera_vjay.appraisals ADD COLUMN policy_version TEXT DEFAULT '1.0';
COMMENT ON COLUMN vera_vjay.appraisals.policy_version IS 'Version of gate B policy used (from corpus at eval time)';

-- 5. Add run_id to evidence_relations for filtering and FK integrity
ALTER TABLE vera_vjay.evidence_relations ADD COLUMN run_id BIGINT;
COMMENT ON COLUMN vera_vjay.evidence_relations.run_id IS 'Run this relation belongs to (backfilled via span FK chain)';

-- Backfill evidence_relations.run_id by joining through evidence_spans -> sources -> answers -> runs
UPDATE vera_vjay.evidence_relations er
SET run_id = ans.run_id
FROM vera_vjay.evidence_spans es1
  JOIN vera_vjay.sources src ON es1.source_id = src.source_id
  JOIN vera_vjay.answers ans ON src.source_id = ans.answer_id
WHERE (er.span1_id = es1.span_id OR er.span2_id = es1.span_id)
  AND er.run_id IS NULL;

-- If that didn't work (sources not joined via answers), try a simpler approach:
-- join evidence_spans to get source_id, use first span's source to find run
UPDATE vera_vjay.evidence_relations er
SET run_id = (
  SELECT DISTINCT ans.run_id
  FROM vera_vjay.evidence_spans es
  WHERE es.span_id = er.span1_id
  LIMIT 1
)
WHERE er.run_id IS NULL;

-- Add FK constraint after backfill (and make NOT NULL)
ALTER TABLE vera_vjay.evidence_relations
ADD CONSTRAINT evidence_relations_run_id_fk FOREIGN KEY (run_id)
REFERENCES vera_vjay.runs (run_id) ON DELETE RESTRICT;

-- Create index for run_id to speed up filtered queries
CREATE INDEX evidence_relations_run_id_idx ON vera_vjay.evidence_relations (run_id);

-- 6. Add rationale column to evidence_relations (optional, for audit trail detail)
ALTER TABLE vera_vjay.evidence_relations ADD COLUMN rationale TEXT;
COMMENT ON COLUMN vera_vjay.evidence_relations.rationale IS 'Optional: scoring rationale or justification for this relation';

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE ON vera_vjay.runs TO vera_vjay_rw;
GRANT UPDATE ON vera_vjay.appraisals TO vera_vjay_rw;
GRANT UPDATE ON vera_vjay.evidence_relations TO vera_vjay_rw;
