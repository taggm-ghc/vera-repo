"""VERA release gate (item #72 W5). Offline by default; exits non-zero on any failure.

Checks: (a) full test suite, (b) frozen-file integrity (sha256), (c) static safety invariants,
(d) optional --live: scope router layer-1-only regression (zero cost, no network).
Scope sets are directional, small n (R72-g): no statistical claim is made. Never prints .env values.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTEST_TIMEOUT_S = 1200
# unsafe_allow_html is permitted only on this escaped line (same allowlist as tests/test_item72_public_mode.py)
UNSAFE_HTML_ALLOWED = {"vera/m7/demo_ui.py": "html.escape(span_text)"}
UI_GLOBS = ("streamlit_app.py", "pages/*.py", "vera/m7/*.py")
ENV_ATTRS = {"getenv", "environ"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ui_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for g in UI_GLOBS:
        out.extend(sorted(root.glob(g)))
    return out


def check_tests(root: Path = ROOT) -> list[str]:
    cmd = [sys.executable, "-m", "pytest", "-q", "tests", "--ignore=tests/test_m2_integration.py"]
    try:
        p = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=PYTEST_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return [f"test suite exceeded {PYTEST_TIMEOUT_S}s"]
    lines = [ln for ln in (p.stdout or "").strip().splitlines() if ln.strip()]
    summary = lines[-1] if lines else "(no output)"
    if p.returncode != 0:
        return [f"pytest exit {p.returncode}: {summary}"] + lines[-15:-1] + (p.stderr or "").strip().splitlines()[-5:]
    print(f"      {summary}")
    return []


def check_frozen(root: Path = ROOT) -> list[str]:
    errs: list[str] = []
    try:
        scope_rec = json.loads((root / "config/scope_router.json").read_text(encoding="utf-8"))["scope_set"]["sha256"]
        trace_rec = json.loads((root / "eval_results/trace_eval_v1.json").read_text(encoding="utf-8"))["questions_sha256"]
    except (OSError, KeyError, ValueError) as exc:
        return [f"cannot read recorded hash: {type(exc).__name__}: {exc}"]
    for rel, rec in (("config/scope_set_v1.json", scope_rec), ("config/trace_questions_v1.json", trace_rec)):
        try:
            actual = sha256_file(root / rel)
        except OSError as exc:
            errs.append(f"{rel}: unreadable ({exc})")
            continue
        if actual != rec:
            errs.append(f"{rel}: sha256 {actual[:12]} != recorded {rec[:12]} (file changed after freeze)")
    return errs


def _is_env_expr(node: ast.AST, tainted: set[str]) -> bool:
    for n in ast.walk(node):
        if isinstance(n, ast.Attribute) and n.attr in ENV_ATTRS:
            return True
        if isinstance(n, ast.Name) and (n.id in tainted or n.id in ENV_ATTRS):
            return True
    return False


def check_no_env_in_widgets(root: Path = ROOT) -> list[str]:
    errs: list[str] = []
    for f in _ui_files(root):
        rel = f.relative_to(root)
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            errs.append(f"{rel}: cannot parse ({exc})")
            continue
        tainted: set[str] = set()
        for _ in range(3):  # propagate through simple assignments
            for n in ast.walk(tree):
                if isinstance(n, ast.Assign) and _is_env_expr(n.value, tainted):
                    tainted |= {t.id for t in n.targets if isinstance(t, ast.Name)}
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                for kw in n.keywords:
                    if kw.arg in ("value", "placeholder", "help", "default") and _is_env_expr(kw.value, tainted):
                        errs.append(f"{rel}:{n.lineno}: environment-derived value passed to widget argument '{kw.arg}'")
    return errs


def check_no_unsafe_html(root: Path = ROOT) -> list[str]:
    errs: list[str] = []
    for f in _ui_files(root):
        rel = str(f.relative_to(root))
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if "unsafe_allow_html" in line and not line.lstrip().startswith("#"):
                if not (rel in UNSAFE_HTML_ALLOWED and UNSAFE_HTML_ALLOWED[rel] in line):
                    errs.append(f"{rel}:{i}: unsafe_allow_html not on an allowlisted escaped line")
    return errs


def check_public_default(root: Path = ROOT) -> list[str]:
    sys.path.insert(0, str(root))
    try:
        from vera import public_mode as pm
        if not pm.is_public_mode({}):
            return ["public mode is NOT the default when VERA_PUBLIC_MODE is unset"]
        return []
    except Exception as exc:  # fail verbosely
        return [f"cannot evaluate public-mode default: {type(exc).__name__}: {exc}"]


def check_live_scope(root: Path = ROOT) -> list[str]:
    """Layer 1 only (mode none: no model call, no network, zero cost), using scope_measure's own helpers.

    Runs in-process and writes nothing, so the recorded measurement under tmp/scope_eval/ is never overwritten.
    """
    import importlib.util
    sys.path.insert(0, str(root))
    try:
        spec = importlib.util.spec_from_file_location("scope_measure_gate", root / "scripts" / "scope_measure.py")
        sm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sm)
        from vera import scope_router as sr
        raw = json.loads(sr.CONFIG_PATH.read_text(encoding="utf-8"))
        doc, _sha = sm.load_set(raw)  # exits (SystemExit) if hash or status is wrong
        cfg = sr.parse_config(raw, layer2_mode="none")
        rows = []
        for item in doc["items"]:
            d = sr.route(item["text"], "none", None, cfg=cfg, chat=None)
            rows.append({"id": item["id"], "label": item["label"], "accepted": d.accepted, "layer": d.layer})
        m = sm.summarise(rows)
    except SystemExit as exc:
        return [f"scope_measure helper exited ({exc.code}); see stderr"]
    except Exception as exc:
        return [f"layer-1 run failed: {type(exc).__name__}: {exc}"]
    print(f"      layer 1 only [directional, small n]: false accepts {m['false_accepts']}/{m['n_out_of_scope']}, "
          f"false refusals {m['false_refusals']}/{m['n_in_scope']} (ids {m['false_refusal_ids']})")
    if m["false_accepts"] > 0:
        return [f"false accepts {m['false_accepts']} > 0 on frozen set (ids {m['false_accept_ids']})"]
    return []


def run_offline_checks(root: Path = ROOT, run_tests: bool = True) -> dict[str, list[str]]:
    results: dict[str, list[str]] = {}
    if run_tests:
        results["(a) test suite"] = check_tests(root)
    results["(b) frozen-file integrity"] = check_frozen(root)
    results["(c1) no env key in widgets"] = check_no_env_in_widgets(root)
    results["(c2) no unsafe_allow_html on model text"] = check_no_unsafe_html(root)
    results["(c3) public mode default"] = check_public_default(root)
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--live", action="store_true", help="also re-run scope router layer 1 only (zero cost; never default)")
    ap.add_argument("--skip-tests", action="store_true", help="skip the test suite (diagnostics only; gate is not a pass)")
    a = ap.parse_args(argv)
    print("VERA release gate")
    if a.skip_tests:
        print("  WARNING: --skip-tests: suite not run; result cannot be a full pass")
    results = run_offline_checks(ROOT, run_tests=not a.skip_tests)
    if a.live:
        results["(d) live scope layer 1"] = check_live_scope(ROOT)
    failed = 0
    for name, errs in results.items():
        print(f"  {'PASS' if not errs else 'FAIL'}  {name}")
        for e in errs:
            print(f"      - {e}")
        failed += bool(errs)
    failed += bool(a.skip_tests)
    print(f"RESULT: {'FAIL' if failed else 'PASS'} ({len(results)} checks, {failed} failed)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
