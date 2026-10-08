"""Item #84 live drill (R1-approved, one-off). Never prints URLs, hosts or keys.

Usage (env: OPENAI_API_KEY, GROQ_API_KEY, VERA_API_KEY, VERA_DB_URL_RO, VERA_DB_URL_WO already in the process):
  memory_recall_drill.py ask QID      # FastAPI TestClient; background tasks run before the call returns
  memory_recall_drill.py recall QID   # fresh process: ask a (related) question and print `recalled`
  memory_recall_drill.py recall-related QID "<related question>"  # ro reader recall ONLY: no /ask, no writes
  memory_recall_drill.py count MINUTES [QID...]  # ro: live memory claims created in the last MINUTES; placeholder check
Questions come from config/trace_questions_v1.json by id.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def question(qid: str) -> str:
    items = json.loads((ROOT / "config" / "trace_questions_v1.json").read_text())["items"]
    return next(i["text"] for i in items if i["id"] == qid)


def client():
    from fastapi.testclient import TestClient
    import main
    os.environ.pop("VERA_DB_URL_RW", None)  # never used by this drill (main's load_dotenv may have loaded it)
    return TestClient(main.app)


def ask(qid: str) -> dict:
    r = client().post("/ask", json={"question": question(qid)}, headers={"X-API-Key": os.environ["VERA_API_KEY"]})
    body = r.json() if r.status_code == 200 else {"detail": str(r.json().get("detail", ""))[:120]}
    return {"status": r.status_code, "recalled": body.get("recalled"), "memory_written": body.get("memory_written"),
            "n_sources": len(body.get("sources") or []), "claim_check": body.get("claim_check"),
            "detail": body.get("detail")}


def count(minutes: int, qids: tuple = ()) -> dict:
    from sqlalchemy import create_engine, text
    cfg = json.loads((ROOT / "config" / "ask-provider-chain.json").read_text())["memory"]["store"]
    eng = create_engine(os.environ[cfg["db_url_ro_env"]], hide_parameters=True)
    p = {"live": cfg["status_live"], "qt": cfg["question_text"], "m": minutes}
    with eng.connect() as c:
        rows = c.execute(text(
            "SELECT c.claim_id, c.created_at FROM vera_vjay.claims c JOIN vera_vjay.answers a ON a.answer_id=c.answer_id "
            "WHERE c.detailed_status=:live AND a.response_text=:qt AND c.created_at > now() - make_interval(mins => :m) "
            "ORDER BY c.claim_id"), p).fetchall()
        ph = c.execute(text(
            "SELECT (SELECT count(*) FROM vera_vjay.questions WHERE research_question=:qt), "
            "(SELECT count(*) FROM vera_vjay.runs WHERE question=:qt), "
            "(SELECT count(*) FROM vera_vjay.questions q JOIN vera_vjay.runs r ON r.question_id=q.question_id "
            " JOIN vera_vjay.answers a ON a.run_id=r.run_id WHERE a.model=:g AND a.response_text=:qt "
            " AND (q.research_question<>:qt OR r.question<>:qt))"), {"qt": cfg["question_text"], "g": cfg["gate_version"]}).fetchone()
        real = [c.execute(text("SELECT (SELECT count(*) FROM vera_vjay.questions WHERE research_question=:t)"
                               " + (SELECT count(*) FROM vera_vjay.runs WHERE question=:t)"
                               " + (SELECT count(*) FROM vera_vjay.answers WHERE response_text=:t)"), {"t": question(q)}).scalar()
                for q in qids]
    return {"real_question_rows_per_qid": real, "new_claim_ids": [r[0] for r in rows], "placeholder_questions": ph[0], "placeholder_runs": ph[1],
            "memory_answer_rows_with_nonplaceholder_question": ph[2]}


def recall_related(qid: str, related: str) -> dict:
    """ro reader's recall only (SELECT). Needs only the ro URL env var; never touches /ask or a write account."""
    from sqlalchemy import create_engine
    from vera.memory_store import RoMemoryReader
    cfg = json.loads((ROOT / "config" / "ask-provider-chain.json").read_text())["memory"]["store"]
    rd = RoMemoryReader(create_engine(os.environ[cfg["db_url_ro_env"]], hide_parameters=True), cfg)
    out = {}
    for label, q in (("qid", question(qid)), ("related", related)):
        rows = rd.recall(q)
        out[label] = {"terms": rd.query_terms(q), "recalled": len(rows), "first": [r["claim_text"][:80] for r in rows]}
    return out


if __name__ == "__main__":
    mode, arg = sys.argv[1], sys.argv[2]
    if mode == "recall-related":
        print(json.dumps(recall_related(arg, sys.argv[3]), default=str))
        sys.exit(0)
    out = count(int(arg), tuple(sys.argv[3:])) if mode == "count" else ask(arg)
    print(json.dumps(out, default=str))
