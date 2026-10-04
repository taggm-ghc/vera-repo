"""Streamlit AppTest for the Trace Eval page, from synthetic JSON files only."""
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent


def _chk(name, applies=True, passed=True):
    return {"name": name, "applies": applies, "passed": passed if applies else None, "reason": "r"}


def _results():
    split = {"n": 2, "errors": 0, "all_pass": 1, "all_pass_rate": 0.5, "wilson95": [0.1, 0.9]}
    pc = {"applies": 2, "passed": 1, "rate": 0.5, "wilson95": [0.1, 0.9]}
    var = {"by_split": {"dev": split}, "per_check": {"A1_citation_present": pc}}
    trace = lambda v: {"id": "q01", "split": "dev", "category": "in_scope_synthesis", "variant": v,
                       "all_pass": True, "error": None, "checks": [_chk("A1_citation_present")],
                       "answer_excerpt": "some words", "sources": [
                           {"n": 1, "url": "https://arxiv.org/abs/1234.5678", "title": "Paper"}]}
    return {"schema": "vera-trace-eval-results-v1", "checks_version": "v", "questions_sha256": "a" * 64,
            "variants": {"baseline": var, "grounded_v1": var}, "traces": [trace("baseline"), trace("grounded_v1")]}


def _validation():
    return {"schema": "vera-trace-check-validation-v1", "positive_class": "FAIL", "labeller": "x",
            "per_check": {"A1_citation_present": {"n": 4, "tp": 2, "tn": 1, "fp": 0, "fn": 1,
                                                  "tpr": 0.67, "tnr": 1.0, "note": ""}},
            "support": {"n": 3, "supported": 1, "partially": 1, "unsupported": 1,
                        "heuristic_tpr": None, "heuristic_tnr": 0.5, "note": ""}}


def _app(results_path, validation_path):
    from vera.trace_eval.ui import render_trace_eval
    render_trace_eval(results_path, validation_path)


@pytest.fixture
def files(tmp_path):
    r, v = tmp_path / "r.json", tmp_path / "v.json"
    r.write_text(json.dumps(_results()))
    v.write_text(json.dumps(_validation()))
    return str(r), str(v), tmp_path


def _run(r, v):
    return AppTest.from_function(_app, kwargs={"results_path": r, "validation_path": v}, default_timeout=30).run()


def test_renders_with_headline_and_validation(files):
    r, v, _ = files
    at = _run(r, v)
    assert not at.exception
    assert len(at.dataframe) >= 3
    assert not any("not yet available" in i.value for i in at.info)
    assert len(at.selectbox) == 2


def test_validation_missing_shows_info(files):
    r, _, tmp = files
    at = _run(r, str(tmp / "absent.json"))
    assert not at.exception
    assert any("Check validation not yet available" in i.value for i in at.info)


def test_missing_results_warns(files):
    _, v, tmp = files
    at = _run(str(tmp / "absent.json"), v)
    assert not at.exception
    assert any("trace_measure.py" in w.value for w in at.warning)


def test_sources_have_no_forbidden_literals():
    for rel in ("vera/trace_eval/ui.py", "pages/trace_eval.py"):
        src = (ROOT / rel).read_text()
        for bad in ("onrender", "localhost", "http://"):
            assert bad not in src, (rel, bad)
