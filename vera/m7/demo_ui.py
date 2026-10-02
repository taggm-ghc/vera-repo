"""VERA demo page renderer. `render_demo(report, source_note)` draws every section from one
eval_report dict (the M6 output), so the page is a pure function of stored data.

Safety: all text that originates from models or the web is shown through st.text/st.markdown
without unsafe HTML, or is html.escape()d before being placed in a <mark> element.
"""
from __future__ import annotations

import html

import streamlit as st

DIM_LABEL = {"relevance": "Relevance", "grounding": "Grounding", "reasoning_integrity": "Reasoning integrity",
             "auditability": "Auditability", "cost_latency": "Cost / latency"}
STATUS_ICON = {"supported": "OK", "partial": "PARTIAL", "unsupported": "UNSUPPORTED", "uncited": "UNCITED",
               "fabricated-citation": "FABRICATED"}


def _safe_link(url) -> str:
    u = str(url or "")
    return f"[{u}]({u})" if u.startswith(("http://", "https://")) else (f"`{u}`" if u else "_no URL_")


def _highlight(span_text: str) -> None:
    st.markdown(f"<mark>{html.escape(span_text)}</mark>", unsafe_allow_html=True)


def _source_info(corpus: dict, span_id: str, audit: dict) -> None:
    sp = (corpus.get("spans") or {}).get(span_id)
    if not sp:
        st.error(f"Span `{span_id}` is not in the evidence corpus (this is what a fabricated citation looks like).")
        return
    src = (corpus.get("sources") or {}).get(sp["source_id"], {})
    _highlight(sp["text"])
    st.markdown(f"**Source:** {src.get('title') or sp['source_id']}  \n{_safe_link(src.get('url'))}")
    st.caption(f"span `{span_id}` chars {sp.get('start')}-{sp.get('end')} | source version {src.get('version')} | "
               f"sha256 `{str(src.get('content_hash') or 'n/a')[:16]}...` | Gate B: {src.get('gate_b_decision')}")


def _outcome_banner(ev: dict) -> None:
    if ev["outcome"] == "success":
        st.success("OUTCOME: SUCCESS. Engineered answer met every required dimension.")
    else:
        names = ", ".join(DIM_LABEL[d] for d in ev["failed_dimensions"])
        st.error(f"OUTCOME: FAILED CASE. Required dimension(s) not met: {names}. "
                 "Recorded as a failed case, not a bad demo.")


def section_answers(rep: dict) -> None:
    st.subheader("Question")
    st.info(rep["question"])
    left, right = st.columns(2)
    with left:
        st.markdown("#### Engineered (VERA)")
        st.markdown(rep["engineered"]["response_text"])
    with right:
        st.markdown(f"#### Baseline (direct {rep['baseline'].get('model', 'LLM')} call)")
        st.markdown(rep["baseline"]["response_text"])


def section_engineered(rep: dict) -> None:
    st.header("1. Engineered response, claim by claim")
    st.caption("Open a claim to see the exact evidence span (highlighted), its source, hash and Gate B decision.")
    labels = {c["id"]: c["label"] for c in rep["evaluation"]["detail"]["engineered"]["grounding"]["claims"]}
    for c in rep["engineered"].get("claims") or []:
        lab = labels.get(c["id"], c.get("verification_status", "?"))
        with st.expander(f"{c['id']} [{STATUS_ICON.get(lab, lab)}]  {c['text'][:110]}"):
            st.markdown(c["text"])
            for sid in c.get("citations", []):
                _source_info(rep["corpus"], sid, rep["engineered"].get("audit", {}))
            if not c.get("citations"):
                st.warning("No citation attached to this claim.")


def section_baseline(rep: dict) -> None:
    st.header("2. Baseline response (for contrast)")
    b = rep["baseline"]
    st.caption(b.get("method", ""))
    st.markdown(b["response_text"])
    g = rep["evaluation"]["detail"]["baseline"]["grounding"]
    st.caption(f"Baseline grounding: {g['traceable_rate']:.0%} of its claims traceable; labels {g.get('label_counts')}.")


def section_eval(rep: dict) -> None:
    st.header("3. Evaluation (5 dimensions)")
    ev = rep["evaluation"]
    _outcome_banner(ev)
    rows = []
    for d, v in ev["dimension_scores"].items():
        chk = ev["success_rule"]["checks"][d]
        rows.append({"Dimension": DIM_LABEL[d], "Engineered (1-5)": v["engineered"], "Baseline (1-5)": v["baseline"],
                     "Winner": v["winner"], "Required test": chk["need"], "Result": chk["got"],
                     "Pass": "PASS" if chk["pass"] else "FAIL"})
    st.dataframe(rows, hide_index=True, use_container_width=True)
    st.caption(f"Dimension wins: {ev['winner_count']}. Wins do not decide the outcome; every required "
               "dimension must pass.")
    for d, v in ev["dimension_scores"].items():
        with st.expander(f"Rationale: {DIM_LABEL[d]}"):
            st.markdown(f"**Engineered:** {v['rationale']}")
            st.markdown(f"**Baseline:** {v['baseline_rationale']}")
    p = ev["scoring_provenance"]
    st.caption(f"Scored by an LLM judge from a different family ({p['judge_family']} / {p['judge_model']}); "
               f"reviewer overrides applied: {p['reviewer_overrides_applied']}; "
               f"disagreements reconciled: {len(p['disagreements'])}. Frozen requirement/objection hash "
               f"`{ev['frozen_requirements_hash']}`.")
    st.warning(p["blinding"])


def _graph_dot(edges: list[dict]) -> str:
    col = {"supports": "darkgreen", "refutes": "red", "qualifies": "orange"}
    lines = ["digraph G { rankdir=LR; node [shape=box, fontsize=10];"]
    for e in edges:
        a, b = (str(e["span1_id"]).replace('"', ""), str(e["span2_id"]).replace('"', ""))
        t = e["relation_type"]
        lines.append(f'"{a}" -> "{b}" [label="{t}", color="{col.get(t, "gray")}", fontcolor="{col.get(t, "gray")}"];')
    return "\n".join(lines) + "\n}"


def section_audit(rep: dict) -> None:
    st.header("4. Audit trail")
    audit, corpus = rep["engineered"].get("audit") or {}, rep["corpus"]
    ta, tb, tc, tr, tv = st.tabs(["Gate A", "Gate B", "Gate C", "Evidence relations", "Claim verification"])
    with ta:
        ga = audit.get("gate_a") or []
        if not ga:
            st.warning("No Gate A records supplied for this run (auditability cannot reach level 5).")
        st.dataframe([{"source": g.get("source_id"), "score": g.get("score"), "decision": g.get("decision"),
                       "url": g.get("url")} for g in ga], hide_index=True, use_container_width=True)
        for g in ga:
            with st.expander(f"Gate A rationale: {g.get('source_id')} (score {g.get('score')})"):
                st.text(str(g.get("rationale")))
    with tb:
        for g in audit.get("gate_b") or []:
            with st.expander(f"{g['span_id']} -> {str(g.get('decision')).upper()} (quality {g.get('overall_quality')})"):
                st.text(f"Rationale: {g.get('rationale')}")
                st.json(g.get("rubric") or {})
                st.caption(f"rubric {g.get('rubric_version')} | policy {g.get('policy_version')}")
    with tc:
        gc = audit.get("gate_c") or {}
        st.markdown(f"**Decision:** `{gc.get('decision')}`  |  **Trace:** {gc.get('trace')}")
        for i, d in enumerate(gc.get("detail") or []):
            with st.expander(f"Adequacy assessment, attempt {i}"):
                st.json(d)
    with tr:
        edges = audit.get("relations") or []
        if edges:
            st.graphviz_chart(_graph_dot(edges))
            st.dataframe(edges, hide_index=True, use_container_width=True)
        else:
            st.info("No evidence relations recorded.")
    with tv:
        g = rep["evaluation"]["detail"]["engineered"]["grounding"]
        st.caption(f"Judge verification of each claim against its cited text. Traceable: {g['traceable_rate']:.0%}; "
                   f"fabricated citations: {g['fabricated']}. Pipeline status: {audit.get('verification_status')}.")
        for c in g["claims"]:
            with st.expander(f"{c['id']}: {STATUS_ICON.get(c['label'], c['label'])}"):
                st.markdown(c["text"])
                st.text(f"Verification: {c['rationale']}")
                for sid in c.get("citations", []):
                    sp = corpus["spans"].get(sid)
                    if sp:
                        _highlight(sp["text"])
        a = rep["evaluation"]["detail"]["engineered"]["auditability"]
        st.markdown("**Randomly sampled audit traces** (seed %s)" % a.get("seed"))
        for t in a.get("sampled", []):
            st.text(f"{t['claim_id']}: level {t['level']} | " + " -> ".join(t["steps"]))


def section_cost(rep: dict) -> None:
    st.header("5. Cost and latency")
    cs, e, b = rep["cost_summary"], rep["engineered"]["usage"], rep["baseline"]["usage"]
    bud = rep["evaluation"]["budget"]

    def row(name, u):
        return {"Run": name, "API calls": u.get("api_calls"), "Tokens": u.get("tokens"),
                "Cost (USD)": u.get("cost_usd"), "Latency (s)": u.get("latency_s")}
    st.dataframe([row("Engineered (M1-M5)", e), row("Baseline (median run)", b)], hide_index=True,
                 use_container_width=True)
    st.caption(f"Budget: ${bud['cost_usd']:.2f} and {bud['latency_s']/60:.0f} min per run. "
               f"Total spend incl. 3 baseline runs and judge: ${cs['cost_usd']:.4f} over {cs['api_calls']} API calls."
               + ("" if cs.get("complete", True) else " WARNING: engineered usage incomplete."))
    with st.expander("Spend breakdown"):
        st.json(cs["breakdown"])


def render_demo(rep: dict, source_note: str = "") -> None:
    st.title("VERA: Verifiable Evidence-based Research Answers")
    if rep.get("is_fixture"):
        st.warning("FIXTURE DATA. This is a placeholder report that exercises the real scorers; "
                   "it is NOT a real VERA run and contains no real findings.")
    st.caption(f"Source: {source_note or 'n/a'} | generated {rep.get('generated_at')}")
    section_answers(rep)
    section_engineered(rep)
    section_baseline(rep)
    section_eval(rep)
    section_audit(rep)
    section_cost(rep)
