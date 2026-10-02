"""End-to-end M4->M5 integration: REAL LLM (cheapest model) + REAL Postgres, inside ONE transaction that is
ALWAYS rolled back. Applies additive migration 004 inside that transaction if not yet deployed (001/003 are owned by M1 and live), seeds an evidence corpus the way M3 would (sources ->
evidence_spans), runs the pipeline, queries every table back, then rolls back so nothing persists.

    VERA_INTEGRATION=1 .venv/bin/python -m pytest tests/test_m4_m5_integration.py -s

Fixture evidence below is a short PARAPHRASED TEST FIXTURE for exercising the pipeline, not verified
extractions of the cited studies; it must not be quoted as research output.
"""
import hashlib
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.skipif(os.getenv("VERA_INTEGRATION") != "1", reason="set VERA_INTEGRATION=1 (uses real LLM + DB)")

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = [  # (title, year, type, sub_questions, text)
    ("Controlled experiment, Copilot task", 2023, "rct", ["sq_controlled"],
     "In a controlled experiment, developers with the assistant completed a JavaScript HTTP-server task 55.8% faster than the control group."),
    ("RCT experienced OSS developers", 2025, "rct", ["sq_controlled", "sq_disagreement"],
     "In a randomized trial with 16 experienced open-source developers working on their own repositories, allowing AI tools made task completion 19% slower, although developers expected a speedup."),
    ("Multi-company field experiments", 2024, "field_experiment", ["sq_field"],
     "Across field experiments at three companies, developers given the assistant completed 26% more tasks per week on average, with larger gains for less experienced developers."),
    ("Enterprise telemetry study", 2024, "observational", ["sq_field", "sq_disagreement"],
     "Telemetry from a large organisation showed modest throughput gains that varied by team and task type."),
    ("Code churn analysis", 2024, "observational", ["sq_quality"],
     "An analysis of repository data reported rising code churn after assistant adoption, which the authors interpret as a possible maintainability concern."),
    ("Security comparison study", 2023, "rct", ["sq_quality"],
     "A user study found participants with an AI assistant wrote less secure code in several tasks and were more confident in its security."),
    ("Perception vs measurement", 2025, "rct", ["sq_disagreement"],
     "Self-reported productivity gains were larger than gains measured by task completion time."),
]


def _apply_004_if_missing(conn):
    """001/003 are live (owned by M1); only apply the additive 004 if absent. DDL is transactional in
    Postgres, so inside this test it is rolled back with everything else."""
    if conn.execute(text("select to_regclass('vera_vjay.gate_c_decisions')")).scalar_one() is None:
        f = next((ROOT / "db" / "migrations").glob("004_vera_*.sql"))
        cur = conn.connection.cursor()  # raw DBAPI cursor, same transaction (SQL may contain literal %)
        cur.execute(f.read_text())
        cur.close()


def _seed(conn):
    qid = conn.execute(text("insert into vera_vjay.questions (research_question) values ('itest: AI assistants and developer productivity') returning question_id")).scalar_one()
    run_id = conn.execute(text("insert into vera_vjay.runs (question_id) values (:q) returning run_id"), {"q": qid}).scalar_one()
    spans = []
    for i, (title, year, typ, sqs, body) in enumerate(FIXTURE):
        url = f"https://example.test/itest/{i}"
        cand = conn.execute(text("insert into vera_vjay.candidates (run_id, source_url, title) values (:r,:u,:t) returning candidate_id"), {"r": run_id, "u": url, "t": title}).scalar_one()
        can = conn.execute(text("insert into vera_vjay.canonical_sources (canonical_url) values (:u) returning canonical_source_id"), {"u": url}).scalar_one()
        src = conn.execute(text("insert into vera_vjay.sources (canonical_source_id, candidate_id, content, content_hash) values (:c,:d,:t,:h) returning source_id"),
                           {"c": can, "d": cand, "t": body, "h": hashlib.sha256(body.encode()).hexdigest()}).scalar_one()
        sid = conn.execute(text("insert into vera_vjay.evidence_spans (source_id, text, start_index, end_index, evidence_type) values (:s,:t,0,:e,:y) returning span_id"),
                           {"s": src, "t": body, "e": len(body), "y": typ}).scalar_one()
        spans.append({"span_id": sid, "source_id": src, "text": body, "sub_question_ids": sqs, "source_title": title, "year": year, "source_type": typ})
    return run_id, {"spans": spans}


def test_end_to_end_engineered_response_in_db():
    sys.path.insert(0, str(ROOT.parent / "AI-Internship" / "ai-engineering-bootcamp-v2" / "week-1v2"))
    from db import get_admin_engine  # noqa: E402

    from vera.m4_m5_runner import run_m4_m5
    from vera.pipeline_store import PipelineStore

    question = "What does published evidence (2023-2026) show about AI coding assistants' effect on developer productivity, and why do the findings disagree?"
    conn = get_admin_engine().connect()
    trans = conn.begin()
    try:
        _apply_004_if_missing(conn)
        run_id, corpus = _seed(conn)
        out = run_m4_m5(str(run_id), question, corpus, store=PipelineStore(conn))
        print("\nGATE C TRACE:", out["gate_c_trace"], "| STATUS:", out["verification_status"], "| REVISED:", out["revised"], "| COST $", out["cost_usd_synthesis_revision"])
        print("FINAL RESPONSE:\n", out["final_response"])
        print("FLAGGED IN DRAFT:", [(u["status"], u["claim_text"][:70]) for u in out["unsupported_claims"]])

        run = conn.execute(text("select engineered_response, verification_status, gate_c_decision, final_answer_id from vera_vjay.runs where run_id=:r"), {"r": run_id}).one()
        assert run.engineered_response == out["final_response"] and run.engineered_response.strip()
        assert run.gate_c_decision == "adequate" and run.final_answer_id == out["final_answer_id"]
        assert conn.execute(text("select count(*) from vera_vjay.gate_c_decisions where run_id=:r"), {"r": run_id}).scalar_one() >= 1
        assert conn.execute(text("select jsonb_typeof(constructed_context) from vera_vjay.reasoning_context where run_id=:r"), {"r": run_id}).scalar_one() == "object"
        stages = [r[0] for r in conn.execute(text("select stage from vera_vjay.answers where run_id=:r order by answer_id"), {"r": run_id})]
        assert stages[0] == "draft" and stages[-1] in ("draft", "revised")
        claims = conn.execute(text("select claim_text, evidence_span_ids, verification_status, detailed_status from vera_vjay.claims where answer_id=:a"), {"a": out["final_answer_id"]}).all()
        assert claims, "final answer must have stored claims"
        valid = {s["span_id"] for s in corpus["spans"]}
        for c in claims:
            assert c.verification_status != "unsupported" and c.evidence_span_ids and set(c.evidence_span_ids) <= valid
        print("STORED CLAIMS:", [(c.detailed_status, c.claim_text[:60]) for c in claims])
    finally:
        trans.rollback()
        conn.close()
