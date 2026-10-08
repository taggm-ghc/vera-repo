"""Streamlit renderer for the TRACE results (item #70; decision guidance added 2026-10-07). Reads only the committed JSON files; no API, DB or env."""
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


def _guidance(res: dict, val: dict | None) -> None:
    from vera.trace_eval import guidance as g

    try:
        cfg = g.load_config()
    except (OSError, ValueError):
        st.info("Decision guidance unavailable: config/trace_eval_guidance.json missing or unreadable.")
        return
    st.subheader("Decision guidance: what this snapshot supports")
    st.caption("Computed from the results and validation files above with the thresholds in "
               "config/trace_eval_guidance.json; re-running the evaluation recomputes everything here.")
    overall, checks = g.compare_overall(res, cfg), g.compare_checks(res, cfg)
    trust = g.check_trust(val, cfg) if val else []
    for line in g.supported_statements(overall, checks, trust, cfg):
        st.markdown(f"- {line}")
    st.markdown("**Is a variant better overall?** (paired, every question)")
    st.dataframe(pd.DataFrame(overall), hide_index=True)
    st.markdown("**Which checks changed?** (paired, questions where the check applies to both variants)")
    st.dataframe(pd.DataFrame(checks), hide_index=True)
    if trust:
        st.markdown("**How far can each check be trusted?** (against the blind labels; positive class = FAIL)")
        st.dataframe(pd.DataFrame(trust), hide_index=True)
    alpha, m = cfg["alpha"], g.min_discordant_for_significance(cfg["alpha"])
    t = cfg["trust"]
    with st.expander("The math behind the indicators"):
        st.markdown("**Pass rate and its 95% range (Wilson score interval)**, for k passes in n questions, "
                    f"with z = Φ⁻¹(1 − α/2) = {g.z_for(alpha):.2f} at α = {alpha}:")
        st.latex(r"\hat p=\frac{k}{n},\qquad \frac{\hat p+\frac{z^2}{2n}\pm z\sqrt{\frac{\hat p(1-\hat p)}{n}+\frac{z^2}{4n^2}}}{1+\frac{z^2}{n}}")
        st.markdown("**Paired comparison (exact McNemar test).** Both variants answer the same questions, so only "
                    "questions where they disagree carry information: b = only the candidate passed, "
                    "c = only the baseline passed.")
        st.latex(r"p=\min\Bigl(1,\;2\sum_{i=0}^{\min(b,c)}\binom{b+c}{i}\Bigl(\tfrac12\Bigr)^{b+c}\Bigr)")
        st.markdown(f"▲/▼ when p < α = {alpha}; ≈ otherwise; · when fewer than {cfg['small_n']} paired questions. "
                    f"Even if every disagreement goes one way, at least {m} disagreeing questions are needed "
                    f"for p < {alpha} (2·½^m < α).")
        st.markdown("**Check trust** (positive class = FAIL): TPR = TP / (TP + FN), the share of real failures the "
                    "check catches; TNR = TN / (TN + FP), the share of good answers it leaves alone; each with a "
                    f"Wilson range. Reliable: TPR ≥ {t['reliable_min_tpr']:.0%} and TNR ≥ {t['reliable_min_tnr']:.0%}. "
                    f"Over-flags: TPR ≥ {t['reliable_min_tpr']:.0%}, TNR lower. Misses failures: TPR ≤ "
                    f"{t['unusable_max_tpr']:.0%}. \"few labels\" when fewer than {cfg['small_n']} real failures or "
                    "good answers were labelled.")
    with st.expander("How to use this for decisions"):
        st.markdown(
            "- **Claim** only ▲ rows, and say the overall result is ≈ unless the overall table shows ▲.\n"
            "- **Fix first**: ▼ rows, then checks marked *misses failures* (their passes say nothing about quality).\n"
            "- **Treat · rows as warning signs**: add questions in those categories before deciding.\n"
            "- **Discount** pass rates on checks that *over-flag*: they understate quality.\n"
            "- **Tune on dev only**; read held-out once at the end, or it stops being a fair test.\n"
            "- **Re-run after each change** and compare the paired tables, not just the headline.")


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
    st.title("VERA Trace Eval")
    res = _load(results_path)
    if res is None:
        st.warning("Results file not found or unreadable. Generate it with: "
                   "`venv/bin/python scripts/trace_measure.py --traces <trace files> --out eval_results/trace_eval_v1.json`")
        return
    sha = str(res.get("questions_sha256") or "n/a")[:12]
    captured = str(res.get("generated_at") or "")[:10] or "unknown"
    st.markdown("30 frozen agent-authored questions (20 dev, 10 held-out). Baseline is /ask as it was at "
                "capture time (a bare gpt-4.1-nano call; /ask may have changed since). The fix, grounded_v1, uses VERA keyless arXiv search, numbered "
                "abstracts and a cite-only rule. Each answer is scored by rule-based checks.")
    st.caption(f"Snapshot captured {captured} (UTC); re-running the evaluation replaces these results and this date. "
               f"checks_version: {res.get('checks_version')} | questions_sha256: {sha}")

    st.subheader("Headline: share of answers that passed every check")
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

    _guidance(res, val)

    _browser(res)

    st.warning("Caveats: questions are agent-authored (self-preference risk); a single agent coded the checks "
               "and labelled the validation set, both from the same model family; n is small; checks are "
               "heuristics validated on dev only; grounding uses abstracts only; arXiv rate limits caused "
               "capture errors, which count as failures.")
