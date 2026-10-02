"""M2 search: question -> ranked, de-duplicated candidate URLs, through a provider chain.

Providers live in vera.search_providers (arXiv first, a hash-frozen seed list as a DISCLOSED fallback). The
chain and its limits come from config/vera_eval_run.json `search`; nothing here needs an API key.

Contract kept for run_m2 / run_mvp: `search_question(question, num_results, *, ledger)` returns
list[dict] with url, title, snippet, rank, provider (plus optional doi, published, licence, ...). On failure
it raises SearchError carrying every attempt's outcome: "search failed" is never returned as "nothing found".
The returned list is a `SearchResults` (a list) whose `.meta` records the route taken.

Routing: a provider that SUCCEEDS with at least `min_candidates` results wins. A failure, or fewer results,
advances to the next provider. If no provider reaches the minimum, the largest result is returned with
meta["below_minimum"]=True (disclosed, never silent). A seed-file provider is used only when the earlier
routes failed or fell short; its use is recorded in meta["fallback_used"].
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import os

import requests

from vera.cost_ledger import CostLedger
from vera.search_providers import ProviderResponseError, SearchConfigError as _SCE, build_chain

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_ROOT = Path(__file__).resolve().parent.parent


class SearchError(RuntimeError):
    pass


class SearchConfigError(_SCE, SearchError):
    """Chain config invalid/unsafe; still a SearchError so existing callers keep working."""


class SearchResults(list):
    """list[dict] plus `.meta` (route record for the run report)."""
    meta: dict

    def __init__(self, items=(), meta=None):
        super().__init__(items)
        self.meta = meta or {}


class _ProviderFailed(Exception):
    def __init__(self, notes):
        super().__init__("; ".join(notes))
        self.notes = notes


def normalize_url(url: str) -> str:
    """Canonical form for de-duplication: lowercase host, no fragment, no trailing slash."""
    p = urlsplit(url.strip())
    path = p.path.rstrip("/") or "/"
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), path, p.query, ""))


def _attempts(provider, question, n, *, ledger, max_retries, backoff_s, deadline_at, timeout_s, sleep, clock):
    notes: list[str] = []
    basis = provider.failure_basis()

    def rec(**kw):
        if ledger:
            ledger.record(kind="search", provider=provider.name, cost_basis=basis, **kw)

    for attempt in range(1, max_retries + 1):
        with provider.gate.lock:  # single connection
            wait = provider.gate.wait_needed(clock())
            if clock() + wait > deadline_at:
                notes.append(f"attempt {attempt}: deadline exceeded before call")
                break
            if wait > 0:
                sleep(wait)
            try:
                resp = provider.call(question, n, timeout_s)
            except _SCE:
                raise
            except requests.RequestException as exc:
                provider.gate.stamp(clock())
                notes.append(f"attempt {attempt}: network error {type(exc).__name__}: {exc}")
                rec(cost_usd=0.0, ok=False, detail=notes[-1], units={"attempt": attempt})
                resp, retry_after = None, None
            else:
                provider.gate.stamp(clock())
        if resp is not None:
            if resp.status_code == 200:
                try:
                    items = provider.parse(resp, n)
                except ProviderResponseError as e:
                    notes.append(f"attempt {attempt}: unusable response: {e}")
                    rec(cost_usd=0.0, ok=False, detail=notes[-1], units={"attempt": attempt})
                    break  # a malformed/error document is not retried
                usd, known, cb = provider.cost_for(resp)
                if ledger:
                    ledger.record(kind="search", provider=provider.name, cost_usd=usd, cost_known=known,
                                  cost_basis=cb, units={"attempt": attempt, "requested": n})
                return items
            notes.append(f"attempt {attempt}: HTTP {resp.status_code} {resp.text[:200]!r}")
            rec(cost_usd=0.0, ok=False, detail=notes[-1], units={"attempt": attempt})
            if resp.status_code not in RETRYABLE_STATUS:
                break
            try:
                retry_after = float(resp.headers.get("Retry-After", ""))
            except ValueError:
                retry_after = None
        wait_s = retry_after if retry_after is not None else backoff_s * 2 ** (attempt - 1)
        if attempt < max_retries:
            sleep(min(wait_s, max(0.0, deadline_at - clock())))
    raise _ProviderFailed(notes)


def _finalize(items, provider_name, n):
    out, seen_url, seen_doi = [], set(), set()
    now = datetime.now(timezone.utc).isoformat()
    for it in items:
        url = (it.get("url") or "").strip()
        sp = urlsplit(url)
        if sp.scheme not in ("http", "https") or not sp.netloc:
            continue
        norm = normalize_url(url)
        doi = (it.get("doi") or "").strip().lower() or None
        if norm in seen_url or (doi and doi in seen_doi):
            continue
        seen_url.add(norm)
        if doi:
            seen_doi.add(doi)
        out.append({**it, "url": url, "title": (it.get("title") or "").strip(),
                    "snippet": (it.get("snippet") or "").strip(), "rank": len(out) + 1,
                    "provider": provider_name, "retrieved_at": now})
        if len(out) >= n:
            break
    return out


def default_chain_and_min():
    from vera.eval_config import load_eval_config
    s = load_eval_config().search
    return build_chain(s, repo_root=_ROOT), int(s["min_candidates"])


def search_question(question: str, num_results: int = 10, *, ledger: CostLedger | None = None, providers=None,
                    min_candidates: int | None = None, max_retries: int = 3, backoff_s: float = 1.0,
                    deadline_s: float = 60.0, timeout_s: float = 20.0, sleep=time.sleep,
                    clock=time.monotonic) -> SearchResults:
    if not question or not question.strip():
        raise ValueError("question must be non-empty")
    if num_results < 1:
        raise ValueError("num_results must be >= 1")
    if providers is None:
        try:
            chain, cfg_min = default_chain_and_min()
        except SearchConfigError:
            raise
        except _SCE as e:
            raise SearchConfigError(str(e)) from None
        except Exception as e:  # noqa: BLE001  (config errors are reported verbosely, never defaulted)
            raise SearchConfigError(f"search configuration unavailable: {type(e).__name__}: {e}") from None
        minimum = cfg_min if min_candidates is None else min_candidates
    else:
        chain, minimum = list(providers), (1 if min_candidates is None else min_candidates)
    minimum = min(minimum, num_results)
    if not chain:
        raise SearchConfigError("no search provider configured")
    missing = [e for p in chain for e in p.required_env if not os.getenv(e)]
    if missing:
        raise SearchConfigError(f"provider(s) need env {missing}")
    deadline_at = clock() + deadline_s  # ONE deadline for the whole chain
    notes, tried, best = [], [], None
    for i, p in enumerate(chain):
        is_seed = p.name.startswith("seed:")
        try:
            raw = _attempts(p, question, num_results, ledger=ledger, max_retries=max_retries, backoff_s=backoff_s,
                            deadline_at=deadline_at, timeout_s=timeout_s, sleep=sleep, clock=clock)
        except _SCE as e:  # unusable config of a route we need: never skipped silently
            raise SearchConfigError(f"{p.name}: {e}") from None
        except _ProviderFailed as f:
            notes += [f"{p.name}: {x}" for x in f.notes]
            tried.append({"provider": p.name, "outcome": "failed"})
            continue
        items = _finalize(raw, p.name, num_results)
        tried.append({"provider": p.name, "outcome": "ok", "count": len(items)})
        if best is None or len(items) > len(best[1]):
            best = (p, items)
        if len(items) >= minimum:
            break
    if best is None:
        raise SearchError("search failed after bounded retries across providers: " + " | ".join(notes))
    p, items = best
    meta = {"route_tried": tried, "route_used": p.name, "min_candidates": minimum,
            "below_minimum": len(items) < minimum, "fallback_used": p.name.startswith("seed:"),
            "provider_endpoint": p.endpoint}
    if meta["fallback_used"]:
        meta["seed_sha256"] = p.expected
    return SearchResults(items, meta)
