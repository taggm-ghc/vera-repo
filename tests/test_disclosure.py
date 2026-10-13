"""Item #74 M2: the public disclosure exists, is on every page, has no URL/host, and matches the memory config."""
import ast
import json
import re
from pathlib import Path
from unittest import mock

from vera import disclosure
from vera.memory_gate import CONFIG_PATH

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["streamlit_app.py", "pages/vera_demo.py", "pages/trace_eval.py"]


def _store() -> dict:
    return json.loads(CONFIG_PATH.read_text())["memory"]["store"]


def test_text_exists_and_states_core_claims():
    t = disclosure.DISCLOSURE_TEXT.lower()
    for phrase in ("ai-generated", "not neutral or complete", "may be wrong", "check the sources",
                   "no profile", "does not save your question"):
        assert phrase in t


def test_render_calls_caption_with_text():
    st = mock.MagicMock()
    disclosure.render_disclosure(st)
    st.caption.assert_called_once_with(disclosure.disclosure_text())


def test_every_page_calls_render_disclosure_once():
    for rel in PAGES:
        tree = ast.parse((ROOT / rel).read_text())
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == "render_disclosure"]
        imported = any(isinstance(n, ast.ImportFrom) and n.module == "vera.disclosure" for n in ast.walk(tree))
        assert imported and len(calls) == 1, rel


def test_pages_do_not_hardcode_the_text():
    for rel in PAGES:
        assert "AI-generated" not in (ROOT / rel).read_text(), rel


def test_no_url_or_host():
    for t in (disclosure.DISCLOSURE_TEXT, disclosure.DISCLOSURE_TEXT_UNCONFIRMED):
        assert not re.search(r"https?://|www\.|\.(com|org|net|io|ai|app)\b|onrender|localhost|\d+\.\d+\.\d+\.\d+", t, re.I)


def test_text_matches_memory_config():
    store = _store()
    chosen = disclosure.disclosure_text().lower()
    if store.get("confirm_required"):
        assert "pending" in chosen and "owner" in chosen
        assert "automatically" not in chosen
    else:
        assert "pending" not in chosen
    # the variant text never claims confirmation when the flag is off, and the pending text always names the owner
    assert "pending" in disclosure.DISCLOSURE_TEXT.lower() and "owner" in disclosure.DISCLOSURE_TEXT.lower()
    assert "pending" not in disclosure.DISCLOSURE_TEXT_UNCONFIRMED.lower()


def test_flag_off_selects_unconfirmed_text(tmp_path):
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"memory": {"store": {"confirm_required": False}}}))
    assert disclosure.disclosure_text(cfg) == disclosure.DISCLOSURE_TEXT_UNCONFIRMED
    assert disclosure.disclosure_text(tmp_path / "missing.json") == disclosure.DISCLOSURE_TEXT
