"""Streamlit renderer for the Week 4 TRACE results. Reads only the committed JSON files; no API, DB or env."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

RESULTS_PATH = "eval_results/trace_eval_v1.json"
VALIDATION_PATH = "eval_results/trace_eval_v1_validation.json"
ARXIV_PREFIX = "https://arxiv.org/"  # Why: the only links the page ever shows, and only if the file supplies them.


def _load(path) -> dict | None:
    p = Path(path)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _ci(w) -> str:
    return f"{w[0]:.2f} to {w[1]:.2f}" if w else "n/a"


def _pct(x) -> str:
    return "n/a" if x is None else f"{x:.0%}"


def _headline(res: dict) -> pd.DataFrame:
    rows = []
    for variant, d in res.get("variants", {}).items():
        for split, s in d.get("by_split", {}).items():
            rows.append({"variant": variant, "split": str(split), "n": s["n"], "errors": s["errors"],
                         "all-pass": s["all_pass"], "rate": _pct(s["all_pass_rate"]),
                         "Wilson 95%": _ci(s.get("wilson95"))})
    return pd.DataFrame(rows)


def _per_check(res: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    variants = list(res.get("variants", {}))
    names = sorted({n for v in variants for n in res["variants"][v].get("per_check", {})})
    table, chart = [], []
    for n in names:
        row, crow = {"check": n}, {"check": n}
        for v in variants:
            c = res["variants"][v].get("per_check", {}).get(n)
            row[f"{v} passed/applies"] = f"{c['passed']}/{c['applies']}" if c else "n/a"
            row[f"{v} rate"] = _pct(c["rate"]) if c else "n/a"
            row[f"{v} Wilson 95%"] = _ci(c.get("wilson95")) if c else "n/a"
            crow[v] = float(c["rate"]) if c and c.get("rate") is not None else 0.0
        table.append(row)
        chart.append(crow)
    return pd.DataFrame(table), pd.DataFrame(chart).set_index("check") if chart else pd.DataFrame()


def _validation(val: dict) -> None:
    st.subheader("Check validation (dev labels)")
    st.caption(f"Positive class: {val.get('positive_class')}; labeller: {val.get('labeller')}")
    rows = [{"check": n, "n": c["n"], "TP": c["tp"], "TN": c["tn"], "FP": c["fp"], "FN": c["fn"],
             "TPR": _pct(c.get("tpr")), "TNR": _pct(c.get("tnr")), "note": c.get("note", "")}
            for n, c in val.get("per_check", {}).items()]
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    s = val.get("support")
    if s:
        st.markdown(f"**Support heuristic (A6)**: n={s['n']}, supported={s['supported']}, "
                    f"partially={s['partially']}, unsupported={s['unsupported']}, "
                    f"TPR={_pct(s.get('heuristic_tpr'))}, TNR={_pct(s.get('heuristic_tnr'))}. {s.get('note', '')}")


def _browser(res: dict) -> None:
    st.subheader("Trace browser")
    traces = res.get("traces", [])
    variants = sorted({t["variant"] for t in traces})
    if not variants:
        st.info("No traces in the results file.")
        return
    variant = st.selectbox("Variant", variants)
    ids = [t["id"] for t in traces if t["variant"] == variant]
    qid = st.selectbox("Question id", ids)
    t = next(t for t in traces if t["variant"] == variant and t["id"] == qid)
    st.markdown(f"Category: `{t['category']}`; split: `{t['split']}`; all-pass: `{t['all_pass']}`")
    if t.get("error"):
        st.error(f"Capture error: {t['error']}")
    st.dataframe(pd.DataFrame([{"check": c["name"], "applies": c["applies"],
                                "passed": "n/a" if c["passed"] is None else str(c["passed"]),
                                "reason": c["reason"]} for c in t["checks"]]), hide_index=True)
    st.markdown("**Answer excerpt (first 25 words)**")
    st.write(t.get("answer_excerpt") or "(none)")
    st.markdown("**Sources**")
    srcs = t.get("sources") or []
    if not srcs:
        st.write("(none)")
    for s in srcs:
        title, url = s.get("title") or "untitled", s.get("url") or ""
        st.markdown(f"- [{title}]({url})" if url.startswith(ARXIV_PREFIX) else f"- {title}")


def render_trace_eval(results_path=RESULTS_PATH, validation_path=VALIDATION_PATH) -> None:
    st.title("VERA Trace Eval (Week 4 TRACE)")
    res = _load(results_path)
    if res is None:
        st.warning("Results file not found or unreadable. Generate it with: "
                   "`venv/bin/python scripts/trace_measure.py --traces <trace files> --out eval_results/trace_eval_v1.json`")
        return
    sha = str(res.get("questions_sha256") or "n/a")[:12]
    st.markdown("30 frozen agent-authored questions (20 dev, 10 held-out). Baseline is the current /ask "
                "(a bare gpt-4.1-nano call). The fix, grounded_v1, uses VERA keyless arXiv search, numbered "
                "abstracts and a cite-only rule. Each answer is scored by rule-based checks.")
    st.caption(f"checks_version: {res.get('checks_version')} | questions_sha256: {sha}")

    st.subheader("Headline: all checks passed")
    st.caption("Directional, small n; capture errors count as failures.")
    st.dataframe(_headline(res), hide_index=True)

    st.subheader("Per check")
    table, chart = _per_check(res)
    st.dataframe(table, hide_index=True)
    if not chart.empty:
        st.bar_chart(chart)

    val = _load(validation_path)
    if val is None:
        st.info("Check validation not yet available")
    else:
        _validation(val)

    _browser(res)

    st.warning("Caveats: questions are agent-authored (self-preference risk); a single agent coded the checks "
               "and labelled the validation set, both from the same model family; n is small; checks are "
               "heuristics validated on dev only; grounding uses abstracts only; arXiv rate limits caused "
               "capture errors, which count as failures.")
