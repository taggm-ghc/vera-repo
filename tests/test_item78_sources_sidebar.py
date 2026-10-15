"""Item #78: 'What VERA draws on' sidebar, read only from shipped files."""
import json
import random
import re
from pathlib import Path

from streamlit.testing.v1 import AppTest

from vera import sources_sidebar as sb

ROOT = Path(__file__).resolve().parent.parent


def test_scope_and_providers_come_from_config():
    assert sb.scope_text() == json.loads((ROOT / "config" / "scope_router.json").read_text())["scope"]
    names = sb.answer_providers()
    assert names[0].startswith("groq ") and names[-1].startswith("openai ")
    assert not any("http" in n or "api_key" in n.lower() for n in names)


def test_snapshot_summary_from_results(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"generated_at": "2030-01-02T00:00:00+00:00", "traces": [
        {"id": "q1", "sources": [{"url": "https://arxiv.org/abs/2401.00001", "title": "A"},
                                 {"url": "https://arxiv.org/abs/2603.12345", "title": "B"}]},
        {"id": "q2", "sources": [{"url": "https://arxiv.org/abs/2401.00001", "title": "A"}]}]}))
    s = sb.snapshot_summary(p)
    assert s["count"] == 2 and s["questions"] == 2 and s["years"] == (2024, 2026) and s["captured"] == "2030-01-02"
    assert sb.snapshot_summary(tmp_path / "missing.json") is None


def test_titles_render_as_plain_text():
    assert sb.plain("[click](javascript:x) *bold*") == r"\[click\]\(javascript:x\) \*bold\*"


def _page():
    import streamlit as st
    from vera.sources_sidebar import render_sources_sidebar
    render_sources_sidebar(st)


def test_sidebar_renders_honest_answer_source_without_hosts_or_dates_in_code():
    at = AppTest.from_function(_page)
    at.run(timeout=30)
    assert not at.exception
    text = " ".join(c.value for c in at.sidebar.caption)
    assert "searches published sources live" in text and "retrieval-augmented generation" in text
    assert "instead of answering from memory" in text
    assert "onrender.com" not in text and "127.0.0.1" not in text
    src = (ROOT / "vera" / "sources_sidebar.py").read_text()
    assert not re.search(r"20\d\d-\d\d-\d\d", src)


def test_every_page_calls_the_sidebar():
    for rel in ("streamlit_app.py", "pages/trace_eval.py", "pages/vera_demo.py"):
        assert "render_sources_sidebar(st)" in (ROOT / rel).read_text(), rel


def test_source_labels_do_not_overclaim_inspection():
    """DEC-EI1: no 'followed back to the original papers', no 'Evidence snapshot'; licences are intermediary-reported."""
    at = AppTest.from_function(_page)
    at.run(timeout=30)
    assert not at.exception
    text = " ".join(c.value for c in at.sidebar.caption)
    assert "followed back" not in text and "original papers" not in text and "Evidence snapshot" not in text
    assert "index record" in text and "search snippets" not in text and "Trace Eval sources" in text
    cap = []

    class St:
        def markdown(self, *a, **k): pass
        def caption(self, t): cap.append(t)

    sb.render_sources(St(), [{"n": 1, "title": "T", "url": "https://x.org/a", "licence_decision": "allow"}],
                      [{"title": "O", "url": "https://x.org/o"}])
    joined = " ".join(cap)
    assert "not verified with the publisher" in joined
    assert "traced from web results to the original source" not in joined and "matched to an index record" in joined
    assert "free abstract" not in joined


def test_licence_caption_absent_without_licence_decision():
    cap = []

    class St:
        def markdown(self, *a, **k): pass
        def caption(self, t): cap.append(t)

    sb.render_sources(St(), [{"n": 1, "title": "T", "url": "https://x.org/a"}], [])
    assert not any("Licence decisions" in c for c in cap)


def test_ui_cap_text_matches_config():
    """The UI strings say '1,500 characters'; pin the config value they describe."""
    cfg = json.loads((ROOT / "config" / "ask-provider-chain.json").read_text())
    assert cfg["grounding"]["snippet_max_chars"] == 1500


# ---- Owner requirement 2026-10-15: the sidebar NEVER discloses a specific individual source/doc/quote ----
_TITLES = ["Zebra Quokka Transformers Revisited", "Obscure Lemur Attention Study", "Plover Gradient Folklore"]
_URLS = ["https://arxiv.org/abs/2401.00001", "https://arxiv.org/abs/2603.12345", "https://example.org/doc/zz-77"]
_QUOTES = ["unmistakable verbatim quote alpha", "another verbatim quote beta"]


def _fixture_snapshot(tmp_path):
    p = tmp_path / "snap.json"
    p.write_text(json.dumps({"generated_at": "2030-01-02T00:00:00+00:00", "traces": [
        {"id": "q1", "sources": [{"url": u, "title": t, "source_id": f"SID-{i}", "snippet": _QUOTES[i % 2],
                                  "quote": _QUOTES[i % 2]} for i, (u, t) in enumerate(zip(_URLS, _TITLES))]}]}))
    return p


def _sidebar_text(monkeypatch, snap_path):
    monkeypatch.setattr(sb, "SNAPSHOT_PATH", snap_path)
    monkeypatch.setattr(sb, "snapshot_summary", lambda path=snap_path, _f=sb.snapshot_summary: _f(path))
    monkeypatch.setattr(sb, "_corpus", lambda st: None)
    cap = []

    class Exp:
        def __enter__(self): return self
        def __exit__(self, *a): return False

    class Side:
        def expander(self, *a, **k): return Exp()

    class St:
        sidebar = Side()
        def caption(self, t): cap.append(t)
        def markdown(self, t): cap.append(t)

    sb.render_sources_sidebar(St())
    return " ".join(cap)


def test_sidebar_never_discloses_individual_sources(tmp_path, monkeypatch):
    text = _sidebar_text(monkeypatch, _fixture_snapshot(tmp_path))
    assert "3 distinct arXiv abstracts" in text  # aggregate still shown
    for needle in _TITLES + _URLS + _QUOTES + ["SID-0", "SID-1", "SID-2", "random sample", "sample of titles", "•"]:
        assert needle not in text, needle


def test_snapshot_summary_has_only_aggregate_fields(tmp_path):
    s = sb.snapshot_summary(_fixture_snapshot(tmp_path))
    assert set(s) == sb.SNAPSHOT_FIELDS
    blob = json.dumps(s)
    for needle in _TITLES + _URLS + _QUOTES:
        assert needle not in blob


def test_sidebar_builder_takes_no_sampling_argument_and_source_has_no_title_sampling():
    import inspect
    assert list(inspect.signature(sb.render_sources_sidebar).parameters) == ["st"]
    body = inspect.getsource(sb.render_sources_sidebar) + inspect.getsource(sb.snapshot_summary)
    assert "sample(" not in body and '"titles"' not in body and "random" not in body


_INTERNAL_TERMS = ["Gate A", "Gate B", "Gate C", "licence gate", "write gate", "admitted by", "DEC-", "vera_vjay",
                   "milestone", "confirm_required"]


def _no_internal_terms(text):
    import re
    assert not re.search(r"#\d{2,3}\b|\bM[1-7]\b|\bitem \d", text), text
    for term in _INTERNAL_TERMS:
        assert term.lower() not in text.lower(), term


def test_sidebar_and_disclosure_show_no_internal_pipeline_terms(tmp_path, monkeypatch):
    from vera import disclosure
    text = _sidebar_text(monkeypatch, _fixture_snapshot(tmp_path))
    _no_internal_terms(text)
    _no_internal_terms(disclosure.DISCLOSURE_TEXT + " " + disclosure.DISCLOSURE_TEXT_UNCONFIRMED)
    cap = []

    class St:
        def caption(self, t): cap.append(t)

    sb.render_corpus(St(), {"summary_source": "agentic_model", "source_count": 19, "corpus_updated_at": "2026-10-13"})
    assert cap[0].startswith("**VERA's corpus:** 19 sources, newest source 2026\\-10\\-13")
    _no_internal_terms(" ".join(cap))
