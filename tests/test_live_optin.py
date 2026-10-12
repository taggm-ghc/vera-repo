"""Owner decision #7: default pytest makes no live calls; live tests need --run-live-stages AND API_BASE_URL."""
from tests.conftest import live_skip_reason


def test_flag_defaults_to_false(pytestconfig):
    assert pytestconfig.getoption("--run-live-stages") is False


def test_live_marker_registered(pytestconfig):
    assert all(any(m.startswith(n + ":") for m in pytestconfig.getini("markers")) for n in ("live", "live_api"))


def test_skip_unless_both_flag_and_env():
    assert "--run-live-stages" in live_skip_reason(False, {"API_BASE_URL": "x"})
    assert live_skip_reason(True, {}) is None  # provider-only live test needs only the flag
    assert "API_BASE_URL" in live_skip_reason(True, {}, needs_api=True)
    assert "API_BASE_URL" in live_skip_reason(True, {"API_BASE_URL": "  "}, needs_api=True)
    assert live_skip_reason(True, {"API_BASE_URL": "x"}, needs_api=True) is None


def test_skip_reason_never_echoes_url():
    assert "secret.example" not in live_skip_reason(False, {"API_BASE_URL": "https://secret.example"}, needs_api=True)


def test_live_tests_skipped_by_default(pytestconfig):
    if pytestconfig.getoption("--run-live-stages"):
        return  # explicit opt-in run; the guard applies to the default run only
    import subprocess, sys
    p = subprocess.run([sys.executable, "-m", "pytest", "tests/test_m4_m5_integration.py", "-q", "-rs"],
                       capture_output=True, text=True, cwd=str(pytestconfig.rootpath), timeout=120,
                       env={k: v for k, v in __import__("os").environ.items() if k != "API_BASE_URL"})
    assert "skipped" in p.stdout and p.returncode == 0 and " passed" not in p.stdout.splitlines()[-1] and " failed" not in p.stdout.splitlines()[-1], p.stdout[-500:]


def test_deprecated_alias_enables_live_with_one_warning(monkeypatch):
    import pytest
    from tests import conftest as c

    class Cfg:
        def getoption(self, name):
            return False

    class Item:
        keywords = {"live": True}
        marks = []

        def add_marker(self, m):
            self.marks.append(m)

    monkeypatch.setenv("VERA_INTEGRATION", "1")
    monkeypatch.setattr(c, "alias_active", lambda env, today=None: True)
    item = Item()
    with pytest.warns(DeprecationWarning, match="--run-live-stages") as rec:
        c.pytest_collection_modifyitems(Cfg(), [item, Item()])
    assert len(rec) == 1 and item.marks == []


def test_live_catalog_test_carries_live_marker():
    from tests import test_sql_contract as t
    marks = getattr(t.test_sql_columns_exist_in_live_catalog, "pytestmark", [])
    assert any(m.name == "live" for m in marks)


def test_gate_live_catalog_outcome_only_passed_succeeds():
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location("release_gate", pathlib.Path(__file__).parents[1] / "scripts" / "release_gate.py")
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    f = g.live_catalog_outcome
    assert f(0, "1 passed in 0.5s")[0] == "PASSED"
    o, why = f(0, "SKIPPED [1] x: no creds\n1 skipped in 0.1s")
    assert o == "SKIPPED" and "credentials not available" in why
    assert f(1, "1 failed in 0.2s")[0] == "FAILED"
    assert f(2, "1 error in 0.2s")[0] == "FAILED"
    assert f(0, "1 passed, 1 skipped in 0.2s")[0] != "PASSED"
    assert f(5, "no tests ran in 0.01s")[0] == "FAILED"
    assert f(0, "no tests ran in 0.01s")[0] == "NO_TESTS"
    assert f(0, "")[0] == "NO_TESTS"
