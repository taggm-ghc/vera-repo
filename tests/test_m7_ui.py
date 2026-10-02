"""Streamlit AppTest: the page renders with no exceptions, from fixture and from a failed case."""
import copy
import os

from streamlit.testing.v1 import AppTest

from vera.m7.fixture import build_fixture_report


def _app(report):
    from vera.m7.demo_ui import render_demo
    render_demo(report, "test")


def _at(report):
    at = AppTest.from_function(_app, kwargs={"report": report}, default_timeout=30)
    return at.run()


def test_fixture_renders_without_exception():
    at = _at(build_fixture_report())
    assert not at.exception
    assert any("FIXTURE DATA" in w.value for w in at.warning)
    assert any("SUCCESS" in s.value for s in at.success)


def test_failed_case_banner():
    rep = build_fixture_report()
    ev = rep["evaluation"]
    ev["outcome"], ev["failed_dimensions"] = "failed_case", ["grounding"]
    at = _at(rep)
    assert not at.exception
    assert any("FAILED CASE" in e.value and "Grounding" in e.value for e in at.error)


def test_fabricated_citation_displays_error_not_crash():
    rep = build_fixture_report()
    rep["engineered"]["claims"][0]["citations"] = ["GHOST"]
    at = _at(rep)
    assert not at.exception
    assert any("not in the evidence corpus" in e.value for e in at.error)


def test_page_file_renders_with_fixture_env(monkeypatch):
    monkeypatch.setenv("VERA_DEMO_SOURCE", "fixture")
    at = AppTest.from_file(os.path.join(os.path.dirname(__file__), "..", "pages", "vera_demo.py"),
                           default_timeout=30).run()
    assert not at.exception
    assert at.title and "VERA" in at.title[0].value
