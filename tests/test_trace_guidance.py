"""Trace Eval decision guidance (2026-10-07): the math, the indicators, and the page section."""
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from vera.trace_eval import guidance as g

ROOT = Path(__file__).resolve().parent.parent
CFG = {"baseline_variant": "baseline", "alpha": 0.05, "small_n": 6,
       "trust": {"reliable_min_tpr": 0.9, "reliable_min_tnr": 0.9, "unusable_max_tpr": 0.5}}


def test_wilson_matches_textbook_value():
    lo, hi = g.wilson(2, 20, g.z_for(0.05))  # 10%, n=20: Wilson 95% about 0.028 to 0.301
    assert lo == pytest.approx(0.0279, abs=1e-3) and hi == pytest.approx(0.3010, abs=1e-3)
    assert g.wilson(0, 0, 1.96) is None


def test_mcnemar_exact_values():
    assert g.mcnemar_exact(9, 0) == pytest.approx(2 / 2 ** 9)
    assert g.mcnemar_exact(3, 2) == 1.0
    assert g.mcnemar_exact(0, 0) == 1.0
    assert g.mcnemar_exact(5, 0) == pytest.approx(0.0625)


def test_min_discordant_for_significance():
    assert g.min_discordant_for_significance(0.05) == 6
    assert g.min_discordant_for_significance(0.01) == 8


def _trace(q, variant, all_pass, checks, split="dev"):
    return {"id": q, "variant": variant, "split": split, "all_pass": all_pass, "error": None,
            "checks": [{"name": n, "applies": True, "passed": p} for n, p in checks.items()]}


def _res(n_better, n_same=0):
    traces = []
    for i in range(n_better):
        traces += [_trace(f"q{i}", "baseline", False, {"A1": False}), _trace(f"q{i}", "cand", True, {"A1": True})]
    for i in range(n_same):
        q = f"s{i}"
        traces += [_trace(q, "baseline", True, {"A1": True}), _trace(q, "cand", True, {"A1": True})]
    return {"traces": traces}


def test_indicators_better_same_and_small():
    assert g.compare_overall(_res(7), CFG)[0]["indicator"] == g.BETTER
    assert g.compare_overall(_res(5, 3), CFG)[0]["indicator"] == g.SAME  # 5 one-way disagreements: p=0.0625
    assert g.compare_overall(_res(3), CFG)[0]["indicator"] == g.SMALL
    assert g.compare_checks(_res(7), CFG)[0]["indicator"] == g.BETTER


def test_errors_count_as_failures():
    res = _res(0, 6)
    for t in res["traces"]:
        if t["variant"] == "cand":
            t["error"] = "SearchError"
    row = g.compare_overall(res, CFG)[0]
    assert row["only baseline passed (c)"] == 6 and row["indicator"] == g.WORSE


def test_trust_indicators():
    val = {"per_check": {"good": {"tp": 10, "fn": 0, "tn": 10, "fp": 0},
                         "over": {"tp": 10, "fn": 0, "tn": 5, "fp": 5},
                         "few": {"tp": 3, "fn": 0, "tn": 3, "fp": 0}},
           "support": {"tp": 0, "fn": 3, "tn": 11, "fp": 0}}
    ind = {r["check"]: r["indicator"] for r in g.check_trust(val, CFG)}
    assert ind["good"] == g.RELIABLE and ind["over"] == g.OVERFLAGS
    assert ind["few"] == g.RELIABLE + " (few labels)"
    assert ind["A6_support (heuristic)"].startswith(g.MISSES)


def test_real_snapshot_statements():
    """The committed snapshot: only A1 and A4 are real gains; A6 misses failures; overall not distinguishable."""
    cfg = g.load_config()
    res = json.loads((ROOT / "eval_results" / "trace_eval_v1.json").read_text())
    val = json.loads((ROOT / "eval_results" / "trace_eval_v1_validation.json").read_text())
    overall, checks, trust = g.compare_overall(res, cfg), g.compare_checks(res, cfg), g.check_trust(val, cfg)
    assert all(r["indicator"] == g.SAME for r in overall)
    assert {r["check"] for r in checks if r["indicator"] == g.BETTER} == {"A1_citation_present", "A4_phantom_evidence"}
    text = " ".join(g.supported_statements(overall, checks, trust, cfg))
    assert "A6_support (heuristic)" in text and "Real regressions" not in text


def _app(results_path, validation_path):
    from vera.trace_eval.ui import render_trace_eval
    render_trace_eval(results_path, validation_path)


def test_page_shows_guidance_and_math_without_date_literals():
    at = AppTest.from_function(_app, args=(str(ROOT / "eval_results" / "trace_eval_v1.json"),
                                           str(ROOT / "eval_results" / "trace_eval_v1_validation.json")))
    at.run(timeout=30)
    assert not at.exception
    subs = [s.value for s in at.subheader]
    # literature-checked order (2026-10-07): context, TL;DR, determinations, decisioning, elaboration, data
    assert subs[:4] == ["Computed determinations", "Decisioning", "Elaboration", "Data"], subs
    assert "Context." in at.markdown[0].value and "TL;DR" in at.info[0].value and "Main caveat" in at.info[0].value
    assert len(at.latex) == 2
    src = (ROOT / "vera" / "trace_eval" / "ui.py").read_text() + (ROOT / "vera" / "trace_eval" / "guidance.py").read_text()
    import re
    assert not re.search(r"20\d\d-\d\d-\d\d", src.split('"""', 2)[-1])  # no date literal outside the docstring
    assert "Week 4" not in "".join(m.value for m in at.markdown) + "".join(t.value for t in at.title)


def test_tldr_from_real_snapshot_and_on_page():
    cfg = g.load_config()
    res = json.loads((ROOT / "eval_results" / "trace_eval_v1.json").read_text())
    val = json.loads((ROOT / "eval_results" / "trace_eval_v1_validation.json").read_text())
    text = g.tldr(g.compare_overall(res, cfg), g.compare_checks(res, cfg), g.check_trust(val, cfg), cfg)
    assert text.startswith("Overall, grounded_v1 is not distinguishable")
    assert "A1_citation_present (p=0.0039)" in text and "A4_phantom_evidence (p=0.0002)" in text
    at = AppTest.from_function(_app, args=(str(ROOT / "eval_results" / "trace_eval_v1.json"),
                                           str(ROOT / "eval_results" / "trace_eval_v1_validation.json")))
    at.run(timeout=30)
    assert not at.exception and at.info and "TL;DR" in at.info[0].value


def test_tldr_reports_regressions():
    cfg = dict(CFG)
    res = _res(0, 0)
    for i in range(7):
        res["traces"] += [_trace(f"w{i}", "baseline", True, {"A1": True}), _trace(f"w{i}", "cand", False, {"A1": False})]
    text = g.tldr(g.compare_overall(res, cfg), g.compare_checks(res, cfg), [], cfg)
    assert "worse" in text and "Real regressions: A1" in text
