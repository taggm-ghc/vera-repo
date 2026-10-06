"""Item #71 (scholarly part) tests: offline only. G2 shared gate, G1 query translation, OpenAlex provider,
fan-out + RRF, G6 dedupe, G8 validators, G7 date mapping. Fixtures are hand-made, never recorded."""
import json
from pathlib import Path

import pytest
import requests

import vera.search_and_fetch as sf
import vera.search_providers as sp
from tests.config_support import load_pair, real_run
from vera.eval_config import EvalConfigError, load_eval_config
from vera.m3.appraisal_rubric import _year
from vera.m3.store import apply_provenance
from vera.search_and_fetch import SearchError, rrf_merge, search_question
from vera.search_providers import (ArxivProvider, OpenAlexProvider, ProviderUnavailable, RateGate,
                                   build_arxiv_query_info, build_chain, reconstruct_abstract)
from vera.search_query import build_query_terms

ROOT = Path(__file__).resolve().parent.parent
CFG = load_eval_config().search
QT = CFG["query_terms"]
QUESTIONS = {q["id"]: q["text"] for q in json.loads((ROOT / "config/trace_questions_v1.json").read_text())["items"]}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("real network transport called in a test")
    monkeypatch.setattr(sp, "arxiv_default_transport", boom)
    monkeypatch.setattr(sp, "openalex_default_transport", boom)
    monkeypatch.setattr(requests, "get", boom)
    monkeypatch.setattr(requests, "post", boom)
    monkeypatch.setattr(sf, "_CHAIN_CACHE", {})


class Resp:
    def __init__(self, status=200, text="", headers=None, payload=None):
        self.status_code, self.text, self.headers, self.payload = status, text, headers or {}, payload


class Fake:
    required_env = ()
    endpoint = "fake"

    def __init__(self, name, seq, interval=0.0, titles=None):
        self.name, self.seq, self.gate, self.calls = name, list(seq), RateGate(interval), []
        self.titles = titles or {}

    def call(self, q, n, t):
        self.calls.append(q)
        x = self.seq.pop(0)
        if isinstance(x, Exception):
            raise x
        return x

    def parse(self, resp, n):
        return [{"url": u, "title": self.titles.get(u, "t"), "snippet": "s"} for u in resp.payload][:n]

    def cost_for(self, resp):
        return 0.0, True, "no_published_price_keyless"

    def failure_basis(self):
        return "no_published_price_keyless"


def ok(*urls):
    return Resp(payload=list(urls))


# ------------------------------------------------------------------------------------------------ G2
def test_default_chain_is_cached_and_gate_shared(monkeypatch):
    built = []

    def fake_build(settings, **kw):
        built.append(1)
        return [Fake("f", [ok("https://a.com/1"), ok("https://a.com/2")], interval=3.0)]
    monkeypatch.setattr(sf, "build_chain", fake_build)
    sleeps = []
    now = [100.0]
    kw = dict(sleep=sleeps.append, clock=lambda: now[0])
    search_question("q one", 5, **kw)
    search_question("q two", 5, **kw)
    assert len(built) == 1, "chain (and its RateGates) must be built once per process and config"
    assert sleeps == [3.0], "second call must wait for the SAME gate"
    c1, _, _ = sf.cached_chain()
    c2, _, _ = sf.cached_chain()
    assert c1 is c2 and c1[0].gate is c2[0].gate


def test_providers_injection_still_works_and_bypasses_cache():
    p = Fake("f", [ok("https://a.com/1")])
    out = search_question("q", 5, providers=[p], sleep=lambda s: None)
    assert [c["url"] for c in out] == ["https://a.com/1"] and sf._CHAIN_CACHE == {}


# ------------------------------------------------------------------------------------------------ G1
def test_terms_drop_meta_words_and_keep_domain_phrases():
    t = build_query_terms(QUESTIONS["q01"], QT)
    assert "developer productivity" in t.core and any(c.startswith("ai coding assistant") for c in t.core)
    for meta in ("published", "evidence", "show", "studies", "what", "about", "does"):
        assert meta not in t.extra and meta not in t.core
    t = build_query_terms(QUESTIONS["q02"], QT)
    assert any(c.startswith("ai coding assistant") for c in t.core)
    assert not {"published", "studies", "find", "do"} & set(t.extra)
    assert "experienced developers" in build_query_terms(QUESTIONS["q02"], QT).core
    t = build_query_terms(QUESTIONS["q06"], QT)
    assert "code security" in t.core and "vulnerabilities" in t.extra
    t = build_query_terms(QUESTIONS["q10"], QT)
    assert any(c.startswith("ai coding assistant") for c in t.core)
    assert not {"published", "studies", "say"} & set(t.extra)


def test_terms_never_empty_query_and_fallback_is_recorded():
    q = {"max_terms": 8, "min_term_chars": 2, "operator": "OR", "submitted_from": "2023-01-01",
         "submitted_to": "2026-12-31"}
    for qid, text in QUESTIONS.items():
        try:
            query, mode = build_arxiv_query_info(text, q, QT)
        except ValueError:
            continue  # no searchable term even in the old path: loud (ValueError), never an empty query
        assert query.strip() and "submittedDate:[20230101" in query and mode
    # nothing survives the new translation: old behaviour, mode says so
    meta_only = "what does published evidence show about such studies"
    assert build_query_terms(meta_only, QT).mode == "fallback_raw"
    query, mode = build_arxiv_query_info(meta_only, q, QT)
    assert mode == "fallback_legacy" and "all:published" in query
    # no config at all: legacy, recorded
    assert build_arxiv_query_info("developer productivity", q)[1] == "legacy_no_terms_config"


def test_arxiv_query_shape_core_and_extra():
    q = CFG["arxiv"]["query"]
    query, mode = build_arxiv_query_info(QUESTIONS["q06"], q, QT)
    assert mode == "core_and_extra"
    assert query.startswith('(all:"') and 'all:"code security"' in query and " AND (all:" in query
    assert "all:published" not in query and "all:evidence" not in query


# ------------------------------------------------------------------------------------------------ OpenAlex
OA = CFG["openalex"]


def oa_work(i, doi=True, inv=True, landing=None):
    return {"id": f"https://openalex.org/W{i}", "doi": f"https://doi.org/10.1000/x{i}" if doi else None,
            "title": f"Paper number {i} on assistants", "publication_year": 2024, "publication_date": f"2024-03-0{i}",
            "type": "article",
            "primary_location": {"landing_page_url": landing, "source": {"display_name": "Journal Z"}},
            "abstract_inverted_index": {"Hello": [0], "world": [1], "again": [2]} if inv else None}


def oa_provider(works, transport=None, **over):
    seen = {}

    def tx(url, params, headers, timeout):
        seen.update(url=url, params=params, headers=headers)
        return Resp(text=json.dumps({"results": works}))
    p = OpenAlexProvider({**OA, **over}, transport=transport or tx, query_terms=QT)
    p.seen = seen
    return p


def test_reconstruct_abstract_order_and_truncate():
    inv = {"b": [1], "a": [0], "c": [2, 3]}
    assert reconstruct_abstract(inv, 100) == "a b c c"
    assert reconstruct_abstract(inv, 3).endswith("...") and reconstruct_abstract(None, 10) == ""


def test_openalex_request_and_parse():
    p = oa_provider([oa_work(1), oa_work(2, doi=False, landing="https://pub.example/2"),
                     oa_work(3, doi=False, landing=None)])
    resp = p.call(QUESTIONS["q06"], 5, 10.0)
    s = p.seen
    assert s["url"] == "https://api.openalex.org/works"
    assert s["params"]["filter"] == "from_publication_date:2023-01-01,to_publication_date:2026-12-31"
    assert s["params"]["per_page"] == 5 and s["params"]["select"] == sp.OPENALEX_SELECT
    assert '"code security"' in s["params"]["search"] and "mailto" not in s["params"]
    items = p.parse(resp, 5)
    assert items[0]["url"] == "https://doi.org/10.1000/x1" and items[0]["doi"] == "10.1000/x1"
    assert items[0]["snippet"] == "Hello world again" and items[0]["published"] == "2024-03-01"
    assert items[0]["publisher"] == "Journal Z" and items[0]["source_type"] == "article"
    assert items[0]["stored_text_kind"] == "abstract_metadata"
    assert items[0]["licence"]["metadata"]["id"] == "CC0-1.0" and items[0]["licence"]["content"]["id"] is None
    assert items[1]["url"] == "https://pub.example/2" and items[2]["url"] == "https://openalex.org/W3"
    assert p.cost_for(resp) == (0.0, True, "keyless_free_allowance")


def test_openalex_bad_bodies_are_failures_not_empty():
    p = oa_provider([])
    with pytest.raises(sp.ProviderResponseError):
        p.parse(Resp(text="<html>"), 5)
    with pytest.raises(sp.ProviderResponseError):
        p.parse(Resp(text=json.dumps({"error": "x"})), 5)
    with pytest.raises(sp.ProviderResponseError):
        oa_provider([], max_response_bytes=1024).parse(Resp(text="x" * 2000), 5)
    assert p.parse(Resp(text=json.dumps({"results": []})), 5) == []


def test_openalex_daily_budget_is_non_retryable_and_chain_skips():
    day = ["2026-10-04"]
    p = oa_provider([oa_work(1)], daily_search_budget=2, today=None)
    p._today = lambda: day[0]
    p.call("developer productivity", 5, 1.0)
    p.call("developer productivity", 5, 1.0)
    with pytest.raises(ProviderUnavailable):
        p.call("developer productivity", 5, 1.0)
    day[0] = "2026-10-05"  # a new day resets the counter
    p.call("developer productivity", 5, 1.0)
    # through the search loop: recorded in notes, other provider still answers
    p2 = oa_provider([oa_work(1)], daily_search_budget=1)
    p2._today = lambda: "d"
    p2.call("developer productivity", 5, 1.0)
    other = Fake("f", [ok("https://a.com/1")])
    out = search_question("developer productivity", 5, providers=[p2, other], sleep=lambda s: None,
                          mode="fan_out")
    assert [c["url"] for c in out] == ["https://a.com/1"]
    assert out.meta["provider_failures"] == ["openalex"]
    assert "budget" in " ".join(out.meta["notes"]) and len(p2.seen) >= 0


def test_openalex_429_is_bounded_and_honours_retry_after():
    sleeps = []
    calls = []

    def tx(*a):
        calls.append(1)
        return Resp(429, text="slow down", headers={"Retry-After": "7"})
    p = OpenAlexProvider(OA, transport=tx, query_terms=QT)
    with pytest.raises(SearchError):
        search_question("developer productivity", 5, providers=[p], sleep=sleeps.append, max_retries=3)
    assert len(calls) == 3 and 7.0 in sleeps


def test_openalex_transport_errors_are_requests_exceptions():
    def tx(*a):
        raise requests.ConnectionError("down")
    p = OpenAlexProvider(OA, transport=tx, query_terms=QT)
    with pytest.raises(requests.RequestException):
        p.call("developer productivity", 5, 1.0)


# ------------------------------------------------------------------------------------------------ fan-out / RRF / G6
def test_rrf_scores_and_order():
    a = [{"url": "https://x.com/1", "title": "alpha one title here"}, {"url": "https://x.com/2", "title": "beta two title here"}]
    b = [{"url": "https://x.com/2", "title": "beta two title here"}, {"url": "https://x.com/3", "title": "gamma three title"}]
    out = rrf_merge({"A": a, "B": b}, 60, 10)
    assert [o["url"] for o in out] == ["https://x.com/2", "https://x.com/1", "https://x.com/3"]
    assert out[0]["rrf_score"] == round(1 / 62 + 1 / 61, 6) and out[0]["found_by_providers"] == ["A", "B"]


def test_fan_out_merges_tolerates_failure_and_records_meta():
    a = Fake("arxiv", [ok("https://a.com/1", "https://a.com/2")])
    b = Fake("openalex", [requests.ConnectionError("x"), requests.ConnectionError("x"), requests.ConnectionError("x")])
    out = search_question("q", 5, providers=[a, b], sleep=lambda s: None, mode="fan_out", min_candidates=1)
    assert [c["rank"] for c in out] == [1, 2] and out.meta["mode"] == "fan_out"
    assert out.meta["provider_counts"] == {"arxiv": 2} and out.meta["provider_failures"] == ["openalex"]
    assert any(n.startswith("openalex:") for n in out.meta["notes"]) and out.meta["route_used"] == "arxiv"
    both = search_question("q", 5, providers=[Fake("arxiv", [ok("https://a.com/1")]),
                                              Fake("openalex", [ok("https://b.com/9")])],
                           sleep=lambda s: None, mode="fan_out")
    assert {c["provider"] for c in both} == {"arxiv", "openalex"} and both.meta["route_used"] == "arxiv+openalex"
    assert both.meta["rrf_k"] == 60


def test_fan_out_all_failed_raises_and_seed_used_only_when_live_empty(tmp_path):
    bad = lambda: Fake("arxiv", [Resp(401, text="no")])
    with pytest.raises(SearchError):
        search_question("q", 5, providers=[bad()], sleep=lambda s: None, mode="fan_out")
    seed = tmp_path / "seed.json"
    doc = {"schema": "vera-seed-v1", "query_agnostic": True,
           "search_strategy": {"queries": ["x"], "tools": "t", "found_at": "d", "inclusion_rule": "r", "agent": "a", "model": "m"},
           "items": [{"url": "https://seed.example/1", "title": "seed title", "snippet": "s", "found_at": "d",
                      "found_by": "a", "reliability_tier": "T1"}]}
    seed.write_text(json.dumps(doc))
    import hashlib
    sha = hashlib.sha256(seed.read_bytes()).hexdigest()
    out = search_question("q", 5, providers=[bad(), sp.SeedFileProvider(seed, sha)], sleep=lambda s: None,
                          mode="fan_out")
    assert out.meta["fallback_used"] and out[0]["url"] == "https://seed.example/1"
    live = Fake("arxiv", [ok("https://a.com/1")])
    out = search_question("q", 5, providers=[live, sp.SeedFileProvider(seed, sha)], sleep=lambda s: None, mode="fan_out")
    assert not out.meta["fallback_used"] and [c["url"] for c in out] == ["https://a.com/1"]


def test_dedupe_by_arxiv_id_doi_and_title_keeps_higher_rank():
    items = [
        {"url": "https://arxiv.org/abs/2401.00001v1", "title": "Same Paper About Copilot", "provider": "arxiv"},
        {"url": "https://doi.org/10.48550/arXiv.2401.00001", "title": "Different title text entirely", "provider": "openalex"},
        {"url": "https://other.example/p", "title": "same paper, about COPILOT!", "provider": "openalex"},
        {"url": "https://doi.org/10.1/abc", "title": "unique one here ok", "doi": "10.1/ABC", "provider": "openalex"},
        {"url": "https://x.example/q", "title": "unique one here ok", "doi": "https://doi.org/10.1/abc", "provider": "arxiv"},
        {"url": "https://x.example/t1", "title": "t", "provider": "a"}, {"url": "https://x.example/t2", "title": "t", "provider": "a"},
    ]
    out = sf._finalize(items, "x", 10)
    assert [o["url"] for o in out] == ["https://arxiv.org/abs/2401.00001v1", "https://doi.org/10.1/abc",
                                       "https://x.example/t1", "https://x.example/t2"]
    assert out[0]["found_by_providers"] == ["arxiv", "openalex"] and out[0]["duplicates_merged"] == 2
    assert out[1]["found_by_providers"] == ["openalex", "arxiv"]
    assert [o["rank"] for o in out] == [1, 2, 3, 4]


# ------------------------------------------------------------------------------------------------ config / G8 / G7
def test_real_config_builds_arxiv_openalex_ddg_chain_without_network():
    chain = build_chain({**CFG, "doaj": {**CFG["doaj"], "enabled": True}}, repo_root=ROOT)  # shipped has DOAJ off
    assert [p.name for p in chain] == ["arxiv", "openalex", "doaj", "duckduckgo_lite"] and CFG["mode"] == "fan_out" and CFG["rrf_k"] == 60
    assert isinstance(chain[1], OpenAlexProvider) and isinstance(chain[0], ArxivProvider)
    assert CFG["openalex"]["daily_search_budget"] == 90 and CFG["openalex"]["min_interval_s"] == 1.0
    assert CFG["openalex"].get("mailto") is None


@pytest.mark.parametrize("edit,msg", [
    (lambda r: r["search"]["openalex"].__setitem__("daily_search_budget", 0), "daily_search_budget"),
    (lambda r: r["search"]["openalex"].__setitem__("endpoint", "http://x"), "openalex.endpoint"),
    (lambda r: r["search"]["openalex"].__setitem__("mailto", "a@b.c"), "mailto"),
    (lambda r: r["search"].__setitem__("mode", "all"), "search.mode"),
    (lambda r: r["search"].__setitem__("rrf_k", 0), "rrf_k"),
    (lambda r: r["search"]["query_terms"].__setitem__("core_phrases", []), "core_phrases"),
    (lambda r: r["search"]["query_terms"].__setitem__("meta_words", ["Show"]), "meta_words"),
    (lambda r: r["search"].pop("query_terms"), "query_terms"),
    (lambda r: r["search"].pop("openalex"), "search.openalex"),
    (lambda r: r["search"]["arxiv"].__setitem__("max_concurrency", 2), "arxiv.max_concurrency"),
])
def test_validators_per_provider(tmp_path, edit, msg):
    with pytest.raises(EvalConfigError, match=msg):
        load_pair(tmp_path, run_edit=edit)


def test_g7_published_reaches_m3_year_reader():
    raw = {"source_id": 1, "provenance": {"published": "2024-03-05T00:00:00Z", "url": "https://x"},
           "source_url": None, "content": None}
    assert _year(raw) is None  # before the mapping the year reader cannot see "published"
    row = apply_provenance(dict(raw))
    assert row["published_date"] == "2024-03-05T00:00:00Z" and _year(row) == 2024
    explicit = apply_provenance({"provenance": {"published": "2020-01-01", "published_date": "2024-01-01"}})
    assert _year(explicit) == 2024


def test_search_probe_script_offline(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("search_probe", ROOT / "scripts" / "search_probe.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "OUT_DIR", tmp_path)

    def fake(q, num_results):
        if "ibuprofen" in q:
            raise SearchError("boom")
        return sf.SearchResults([{"url": f"https://a.com/{i}", "title": "T", "snippet": "s" * 400, "rank": i,
                                  "provider": "arxiv", "published": "2024-01-01"} for i in range(1, 8)], {"mode": "fan_out"})
    assert mod.main(["--label", "t", "--ids", "q01", "q23"], search=fake) == 1
    rows = [json.loads(x) for x in (tmp_path / "t.jsonl").read_text().splitlines()]
    assert len([r for r in rows if r["question_id"] == "q01"]) == 5 and len(rows[0]["snippet"]) == 300
    assert rows[-1]["question_id"] == "q23" and "boom" in rows[-1]["error"]
    assert mod.main(["--label", "bad/label", "--ids", "q01"], search=fake) == 2
