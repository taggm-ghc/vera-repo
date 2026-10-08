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
