"""M1 round-trip test for the vera_vjay schema (runs against PRODUCTION Postgres).

    cd <week-1v2 dir> && .venv/bin/python <this file>

Flow: question -> run -> search_iteration -> candidate (Gate A) -> fetch+hash
source -> query back through the full chain -> verify -> immutability checks ->
CLEAN UP every test row (always, even on failure) and confirm zero remain.
Test rows are tagged with a unique marker in research_question.
"""
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "AI-Internship" / "ai-engineering-bootcamp-v2" / "week-1v2"))
from db import get_admin_engine  # noqa: E402
from sqlalchemy import text  # noqa: E402

TEST_URL = "https://example.com/"
FALLBACK = "Example Domain (offline fallback content used because the fetch failed)"
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, bool(ok), detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name} {detail}")


def fetch() -> tuple[str, dict]:
    import requests
    try:
        r = requests.get(TEST_URL, timeout=10, headers={"User-Agent": "vera-m1-roundtrip/1.0"})
        r.raise_for_status()
        return r.text, {"url": TEST_URL, "http_status": r.status_code, "content_type": r.headers.get("content-type"), "fetcher": "requests"}
    except Exception as exc:
        return FALLBACK, {"url": TEST_URL, "fetcher": "offline-fallback", "fetch_error": type(exc).__name__}


def main() -> int:
    t0 = time.perf_counter()
    marker = f"M1-ROUNDTRIP-TEST-{uuid.uuid4()}"
    engine = get_admin_engine()
    qid = None
    SNAP = "SELECT md5(string_agg(concat_ws('|',candidate_id,run_id,source_url,title,snippet,gate_a_score,gate_a_rationale,fetch_status,created_at),E'\n' ORDER BY candidate_id)), count(*) FROM vera_vjay.candidates WHERE candidate_id <= :mx AND source_url NOT LIKE '%M1-ROUNDTRIP-TEST-%'"
    with engine.connect() as c:
        mx = c.execute(text("SELECT coalesce(max(candidate_id),0) FROM vera_vjay.candidates")).scalar_one()
        before = tuple(c.execute(text(SNAP), {"mx": mx}).one())
    try:
        with engine.begin() as c:
            qid = c.execute(text("INSERT INTO vera_vjay.questions (research_question, governing_context, evidence_requirements_map) "
                                 "VALUES (:q, 'm1 test', CAST(:m AS jsonb)) RETURNING question_id"),
                            {"q": marker, "m": '{"subquestions": ["rct", "telemetry"]}'}).scalar_one()
            run_id = c.execute(text("INSERT INTO vera_vjay.runs (question_id, baseline_response) VALUES (:q, 'baseline') RETURNING run_id"), {"q": qid}).scalar_one()
            it_id = c.execute(text("INSERT INTO vera_vjay.search_iterations (run_id, search_query, rank, results_count) "
                                   "VALUES (:r, 'ai coding assistant productivity', 1, 1) RETURNING iteration_id"), {"r": run_id}).scalar_one()
            url = TEST_URL + "?" + marker
            cand_id = c.execute(text("INSERT INTO vera_vjay.candidates (run_id, search_iteration_id, source_url, title, snippet, gate_a_score, gate_a_decision, gate_a_rationale) "
                                     "VALUES (:r, :i, :u, 't', 's', 0.85, 'fetch', 'test rationale') RETURNING candidate_id"),
                                {"r": run_id, "i": it_id, "u": url}).scalar_one()
            content, prov = fetch()
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            canon = c.execute(text("INSERT INTO vera_vjay.canonical_sources (canonical_url) VALUES (:u) RETURNING canonical_source_id"), {"u": url}).scalar_one()
            src_id = c.execute(text("INSERT INTO vera_vjay.sources (canonical_source_id, candidate_id, version, content, content_hash, provenance) "
                                    "VALUES (:cs, :c, 1, :ct, :h, CAST(:p AS jsonb)) RETURNING source_id"),
                               {"cs": canon, "c": cand_id, "ct": content, "h": digest, "p": json.dumps(prov)}).scalar_one()
            c.execute(text("UPDATE vera_vjay.candidates SET fetch_status='fetched' WHERE candidate_id=:c"), {"c": cand_id})

        print("Query back: question -> run -> candidate -> source -> hash")
        with engine.connect() as c:
            row = c.execute(text(
                "SELECT q.research_question, q.evidence_requirements_map->'subquestions'->>0 AS sq, r.run_id, ca.gate_a_score, ca.gate_a_decision, ca.fetch_status, "
                "si.search_query, s.content, s.content_hash, s.hash_algorithm, s.version, s.provenance->>'url' AS purl "
                "FROM vera_vjay.questions q JOIN vera_vjay.runs r USING (question_id) "
                "JOIN vera_vjay.candidates ca USING (run_id) JOIN vera_vjay.search_iterations si ON si.iteration_id = ca.search_iteration_id "
                "JOIN vera_vjay.sources s USING (candidate_id) WHERE q.question_id = :q"), {"q": qid}).mappings().one()
        check("question persisted", row["research_question"] == marker)
        check("JSONB map persisted", row["sq"] == "rct")
        check("run linked", row["run_id"] == run_id)
        check("Gate A score/decision persisted", float(row["gate_a_score"]) == 0.85 and row["gate_a_decision"] == "fetch")
        check("fetch_status updated separately", row["fetch_status"] == "fetched")
        check("search iteration linked", row["search_query"] == "ai coding assistant productivity")
        check("content stored", row["content"] == content, f"({len(content)} chars, fetcher={prov['fetcher']})")
        check("hash round-trips (recomputed from stored content)", hashlib.sha256(row["content"].encode()).hexdigest() == row["content_hash"] == digest)
        check("version/algorithm/provenance", row["version"] == 1 and row["hash_algorithm"] == "sha256" and row["purl"] == TEST_URL)

        print("Constraint + immutability checks (each in a rolled-back transaction)")

        def must_fail(name, sql, params=None, role=None):
            try:
                with engine.begin() as c:
                    if role:
                        c.execute(text(f"SET LOCAL ROLE {role}"))
                    c.execute(text(sql), params or {})
                check(name, False, "statement unexpectedly succeeded")
            except Exception as exc:
                check(name, True, f"({type(getattr(exc, 'orig', exc)).__name__})")

        must_fail("UPDATE on sources blocked by trigger", "UPDATE vera_vjay.sources SET content='x' WHERE source_id=:s", {"s": src_id})
        must_fail("app role cannot DELETE sources", "DELETE FROM vera_vjay.sources WHERE source_id=:s", {"s": src_id}, role="vera_vjay_rw")
        must_fail("duplicate (canonical, hash) rejected", "INSERT INTO vera_vjay.sources (canonical_source_id, candidate_id, version, content, content_hash) VALUES (:cs,:c,2,'x',:h)",
                  {"cs": canon, "c": cand_id, "h": digest})
        must_fail("gate_a_score > 1 rejected", "UPDATE vera_vjay.candidates SET gate_a_score=1.5 WHERE candidate_id=:c", {"c": cand_id})
        must_fail("invalid fetch_status rejected", "UPDATE vera_vjay.candidates SET fetch_status='bogus' WHERE candidate_id=:c", {"c": cand_id})
        must_fail("scored candidate without decision rejected", "INSERT INTO vera_vjay.candidates (run_id, source_url, gate_a_score) VALUES (:r,'u-nodecision',0.5)", {"r": run_id})
    except Exception as exc:
        check("test body completed without exception", False, f"{type(exc).__name__}: {exc}")
    finally:
        print("Cleanup")
        if qid is not None:
            with engine.begin() as c:
                p = {"q": qid}
                runs = "SELECT run_id FROM vera_vjay.runs WHERE question_id=:q"
                cands = f"SELECT candidate_id FROM vera_vjay.candidates WHERE run_id IN ({runs})"
                c.execute(text("CREATE TEMP TABLE _vt_canon ON COMMIT DROP AS SELECT DISTINCT canonical_source_id FROM vera_vjay.sources "
                               f"WHERE candidate_id IN ({cands})"), p)
                for sql in (f"DELETE FROM vera_vjay.sources WHERE candidate_id IN ({cands})",
                            "DELETE FROM vera_vjay.canonical_sources WHERE canonical_source_id IN (SELECT canonical_source_id FROM _vt_canon)",
                            f"DELETE FROM vera_vjay.candidates WHERE run_id IN ({runs})",
                            f"DELETE FROM vera_vjay.search_iterations WHERE run_id IN ({runs})",
                            "DELETE FROM vera_vjay.runs WHERE question_id=:q",
                            "DELETE FROM vera_vjay.questions WHERE question_id=:q"):
                    c.execute(text(sql), p)
            with engine.connect() as c:
                left = c.execute(text("SELECT (SELECT count(*) FROM vera_vjay.questions WHERE research_question LIKE 'M1-ROUNDTRIP-TEST-%') "
                                      "+ (SELECT count(*) FROM vera_vjay.canonical_sources WHERE canonical_url LIKE '%M1-ROUNDTRIP-TEST-%') "
                                      "+ (SELECT count(*) FROM vera_vjay.candidates WHERE source_url LIKE '%M1-ROUNDTRIP-TEST-%')")).scalar_one()
            check("all test rows removed", left == 0, f"({left} remaining)")
    with engine.connect() as c:
        after = tuple(c.execute(text(SNAP), {"mx": mx}).one())
    check("pre-existing candidates untouched", before == after, f"({before[1]} rows, checksum {'same' if before == after else 'CHANGED'})")
    elapsed = time.perf_counter() - t0
    failed = [n for n, ok, _ in results if not ok]
    print(f"\n{'PASS' if not failed else 'FAIL'}: {len(results) - len(failed)}/{len(results)} checks in {elapsed:.2f}s")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
