# STUB. The M3 instance's original conftest (FakeLLM(**{"m3.x": ...}), domains()) was accidentally
# overwritten by the M4/M5 instance and must be restored by the M3 owner. M4/M5 tests use
# tests/m45_support.py and do not depend on this file.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# Owner decision #7: live tests (real LLM/provider calls, deployed API) run only on explicit opt-in:
#   pytest tests --run-live-stages                      (provider-only live tests: marker `live`)
#   API_BASE_URL=... pytest tests --run-live-stages     (tests that call the deployed VERA API: marker `live_api`)
# `live_api` tests also need API_BASE_URL. No persistent environment switch exists.
import datetime
import os
import warnings

import pytest

# Deprecated alias for the old gate (VERA_INTEGRATION=1); honoured through this date, then ignored.
ALIAS_LAST_DAY = datetime.date(2026, 10, 25)


def pytest_addoption(parser):
    parser.addoption("--run-live-stages", action="store_true", default=False,
                     help="run tests marked 'live'/'live_api' (live_api also needs API_BASE_URL in the environment)")


def pytest_configure(config):
    config.addinivalue_line("markers", "live: makes live provider calls; needs --run-live-stages")
    config.addinivalue_line("markers", "live_api: calls the deployed VERA API; needs --run-live-stages and API_BASE_URL")


def alias_active(env, today=None) -> bool:
    today = today or datetime.date.today()
    return env.get("VERA_INTEGRATION") == "1" and today <= ALIAS_LAST_DAY


def live_skip_reason(flag: bool, env, needs_api: bool = False) -> str | None:
    """Reason a live test must be skipped, or None. Names the missing piece, never the URL value."""
    missing = []
    if not flag:
        missing.append("--run-live-stages not passed")
    if needs_api and not str(env.get("API_BASE_URL", "")).strip():
        missing.append("API_BASE_URL not set")
    return ("live test skipped: " + "; ".join(missing)) if missing else None


def pytest_collection_modifyitems(config, items):
    flag = config.getoption("--run-live-stages")
    if not flag and alias_active(os.environ):
        warnings.warn("VERA_INTEGRATION=1 is a deprecated alias for --run-live-stages and stops working "
                      "after 2026-10-25; pass --run-live-stages instead.", DeprecationWarning, stacklevel=1)
        flag = True
    for item in items:
        api = "live_api" in item.keywords
        if api or "live" in item.keywords:
            reason = live_skip_reason(flag, os.environ, needs_api=api)
            if reason:
                item.add_marker(pytest.mark.skip(reason=reason))
