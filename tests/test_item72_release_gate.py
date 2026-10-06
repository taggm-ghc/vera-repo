"""Offline checks of scripts/release_gate.py (item #72 W5). Temp copies only; no network, no subprocess suite run."""
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("release_gate", ROOT / "scripts" / "release_gate.py")
rg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rg)


@pytest.fixture
def tree(tmp_path):
    for rel in ("config/scope_router.json", "config/scope_set_v1.json", "config/trace_questions_v1.json",
                "eval_results/trace_eval_v1.json", "streamlit_app.py"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, tmp_path / rel)
    (tmp_path / "pages").mkdir()
    return tmp_path


def test_real_repo_offline_checks_pass():
    res = rg.run_offline_checks(ROOT, run_tests=False)
    assert all(not v for v in res.values()), res


def test_frozen_scope_set_change_detected(tree):
    assert rg.check_frozen(tree) == []
    p = tree / "config/scope_set_v1.json"
    p.write_text(p.read_text(encoding="utf-8") + " ", encoding="utf-8")
    errs = rg.check_frozen(tree)
    assert len(errs) == 1 and "scope_set_v1.json" in errs[0]


def test_frozen_trace_set_change_detected(tree):
    p = tree / "config/trace_questions_v1.json"
    p.write_text(p.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert any("trace_questions_v1.json" in e for e in rg.check_frozen(tree))


def test_missing_recorded_hash_fails_verbosely(tree):
    (tree / "eval_results/trace_eval_v1.json").write_text(json.dumps({}), encoding="utf-8")
    errs = rg.check_frozen(tree)
    assert errs and "cannot read recorded hash" in errs[0]


@pytest.mark.parametrize("src", [
    'import os, streamlit as st\nst.text_input("k", value=os.getenv("K"))\n',
    'import os, streamlit as st\nkey = os.environ.get("K", "")\nst.text_input("k", value=key)\n',
    'import os, streamlit as st\nk = os.getenv("K")\nj = k or ""\nst.text_input("k", value=j, type="password")\n',
])
def test_env_key_in_widget_detected(tree, src):
    (tree / "pages" / "bad.py").write_text(src, encoding="utf-8")
    errs = rg.check_no_env_in_widgets(tree)
    assert any("pages/bad.py" in e for e in errs), errs


def test_clean_widget_not_flagged(tree):
    (tree / "pages" / "ok.py").write_text('import streamlit as st\nst.text_input("k", value="")\n', encoding="utf-8")
    assert rg.check_no_env_in_widgets(tree) == []


def test_unsafe_allow_html_detected_and_comment_ignored(tree):
    (tree / "pages" / "bad.py").write_text('import streamlit as st\nst.markdown(ans, unsafe_allow_html=True)\n', encoding="utf-8")
    (tree / "pages" / "ok.py").write_text('# unsafe_allow_html is banned\n', encoding="utf-8")
    errs = rg.check_no_unsafe_html(tree)
    assert len(errs) == 1 and "pages/bad.py:2" in errs[0]


def test_public_default_check_reports_pass_and_failure(monkeypatch):
    assert rg.check_public_default(ROOT) == []
    from vera import public_mode as pm
    monkeypatch.setattr(pm, "is_public_mode", lambda env=None: False)
    assert rg.check_public_default(ROOT)


def test_live_layer1_zero_false_accepts_on_frozen_set(capsys):
    assert rg.check_live_scope(ROOT) == []
    assert "directional, small n" in capsys.readouterr().out
