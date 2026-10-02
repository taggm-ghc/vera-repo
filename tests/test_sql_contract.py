"""C4 contract test: every column named in SQL under vera/ and sql/ exists on its live table.

Introspects information_schema.columns for schema vera_vjay ONLY, read-only, as vera_eval_ro.
Skips (never fails) when credentials or the DB are unavailable. See sql_contract_support for
extractor limits. The extractor unit tests below need no DB.
"""
import pytest

from tests import sql_contract_support as sc


def test_extractor_unit():
    cols = sc.extract_columns("SELECT a.x, a.y FROM {S}.appraisals a JOIN {S}.sources s ON s.source_id=a.source_id")
    assert {("appraisals", "x"), ("appraisals", "y"), ("sources", "source_id")} <= cols
    cols = sc.extract_columns("UPDATE {S}.runs SET baseline_response=:b, eval_metrics=CAST(:m AS jsonb) WHERE run_id=:r")
    assert {("runs", "baseline_response"), ("runs", "eval_metrics"), ("runs", "run_id")} <= cols
    cols = sc.extract_columns("INSERT INTO {S}.answers (run_id, stage) VALUES (:r,:s) RETURNING answer_id")
    assert {("answers", "run_id"), ("answers", "stage"), ("answers", "answer_id")} <= cols
    assert ("appraisals", "bogus_col") in sc.extract_columns("SELECT bogus_col FROM vera_vjay.appraisals WHERE source_id=:s")


def test_extractor_finds_statements():
    found = sc.collect()
    assert len(found) > 40, f"extractor found only {len(found)} (table,column) pairs; parser regression?"
    assert ("appraisals", "rubric_version") in found


def test_sql_columns_exist_in_live_catalog():
    try:
        conn = sc.ro_connection()
    except Exception as e:  # noqa: BLE001 - any connect failure means "cannot verify", not "contract broken"
        pytest.skip(f"live catalog unreachable ({type(e).__name__})")
    if conn is None:
        pytest.skip("read-only DB credentials absent (VERA_DB_PASSWORD_vera_eval_ro / .env.db-accounts)")
    try:
        cat = sc.live_catalog(conn)
    finally:
        conn.close()
    if not cat:
        pytest.skip("schema vera_vjay has no visible columns for this account")
    found = sc.collect()
    problems = []
    for (t, c), where in sorted(found.items()):
        if t not in cat:
            problems.append(f"table vera_vjay.{t} missing (used at {', '.join(where[:3])})")
        elif c not in cat[t]:
            problems.append(f"vera_vjay.{t}.{c} missing (used at {', '.join(where[:3])})")
    assert not problems, "SQL/catalog mismatches:\n" + "\n".join(problems)
