"""Search provider interface and the two providers of the M2 redo (plan vera-plan-m2-keyless-search.md).

  * `SearchProvider` is the seam `vera.search_and_fetch.search_question` drives. A provider knows how to make
    ONE request (`call`), turn the response into candidate dicts (`parse`), say what the call cost
    (`cost_for`) and how politely it must be called (`gate`).
  * `ArxivProvider` (first route): keyless, abstract pages only (see ARXIV_* constants for why).
  * `SeedFileProvider` (DISCLOSED FALLBACK): an agent-prepared candidate list read from a file that is frozen
    by sha256 (a changed file is a different run input and is refused).

Real network access exists in exactly one place per networked provider: `arxiv_default_transport`. Tests patch
it to raise. The seed provider never touches the network.

EXTENSION SEAM (R1 D5, last resort only): a provider for a hosted web-search tool would implement the same
`SearchProvider` protocol and be registered in `PROVIDER_FACTORIES`. NONE exists: no code path here spends
money, uses a key, or can be selected by config (an unknown provider name is a SearchConfigError).
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Protocol
from urllib.parse import urlsplit

# Why: names the cost basis recorded on every ledger record of a keyless provider. Research found no
# published price on the pages read, but also no terms text stating $0, so the basis says exactly that
# (plan section 12, SC4 "qualified"). The cost is recorded as KNOWN $0: an unknown cost would stop every
# scored run before M6 with exit 4 (run_mvp.stop_if_cost_unknown).
COST_BASIS_KEYLESS = "no_published_price_keyless"
# Why: a seed list is prepared out of band; inside the run its cost is truly 0, the discovery cost is not
# metered by VERA and is disclosed in run_mvp.DIVERGENCES.
COST_BASIS_SEED = "out_of_band_seed"

# Why: arXiv's API terms put DESCRIPTIVE METADATA under CC0 1.0 but forbid storing and serving e-prints
# without the copyright holder's permission or a permissive licence (plan 12.3 SC3, evidence arxiv-terms).
# CC0 is therefore recorded as a METADATA licence only and is never read as permission to store a paper.
ARXIV_METADATA_LICENCE = {"id": "CC0-1.0", "url": "https://creativecommons.org/publicdomain/zero/1.0/",
                          "source": "arxiv_api_terms"}
# Why: R1 approval: only the abstract page (https://arxiv.org/abs/<id>) is ever a candidate. HTML, PDF and
# e-print URLs are never emitted, because fetching them would store the paper itself.
ARXIV_ABSTRACT_PATH_PREFIX = "/abs/"
ARXIV_HOST = "arxiv.org"
# Why: a response over this size is not an Atom page of <=100 entries; refuse before parsing (the real value
# is config search.arxiv.max_response_bytes; this is only the validator's absolute ceiling).
MAX_RESPONSE_BYTES_CEILING = 8 * 1024 * 1024
# Why: no contact e-mail is sent to any API (R1 has not approved one), so the identifier names only the tool.
USER_AGENT = "VERA-research-pipeline/1.0 (offline-reviewed; no contact address configured)"
# Why: the frozen question is prose; arXiv searches terms. These words carry no topic signal, so they are
# dropped before the term query is built. Deliberately small and plain: the effect on recall is UNMEASURED
# (plan L1 measures it).
QUERY_STOPWORDS = frozenset(
    "a an and are as at be been but by can did do does for from has have how in into is it its of on or "
    "that the their them these this those to was were what when which who why with would your".split())
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"
SEED_SCHEMA = "vera-seed-v1"
SEED_ITEM_REQUIRED = ("url", "title", "snippet", "found_at", "found_by", "reliability_tier")


class SearchConfigError(RuntimeError):
    """Chain/provider configuration is invalid or unsafe (declared in vera.search_and_fetch as a SearchError
    subclass; defined here so providers can raise it without an import cycle)."""


class ProviderResponseError(RuntimeError):
    """The provider answered HTTP 200 but the body is not a usable result (an error document, malformed XML,
    an oversized body). A failure, NEVER an empty result."""


class HttpLike(Protocol):
    status_code: int
    text: str
    headers: Mapping[str, str]


@dataclass
class RateGate:
    """Per-provider politeness: minimum interval between calls and ONE connection at a time (lock)."""
    min_interval_s: float
    last_end: float | None = None

    def __post_init__(self):
        self.lock = threading.Lock()

    def wait_needed(self, now: float) -> float:
        if self.last_end is None:
            return 0.0
        return max(0.0, self.last_end + self.min_interval_s - now)

    def stamp(self, now: float) -> None:
        self.last_end = now


class SearchProvider(Protocol):
    name: str
    endpoint: str
    required_env: tuple[str, ...]
    gate: RateGate

    def call(self, query: str, n: int, timeout_s: float) -> HttpLike: ...
    def parse(self, resp: HttpLike, n: int) -> list[dict]: ...
    def cost_for(self, resp: HttpLike) -> tuple[float, bool, str]: ...
    def failure_basis(self) -> str: ...


# ----------------------------------------------------------------------------------------- licence records
def licence_record(metadata: dict | None = None, content: dict | None = None) -> dict:
    none = {"id": None, "url": None, "source": "none"}
    return {"metadata": dict(metadata) if metadata else dict(none),
            "content": dict(content) if content else dict(none)}


# ----------------------------------------------------------------------------------------- arXiv
def arxiv_default_transport(url: str, params: dict, headers: dict, timeout: float):
    """THE one real network call for arXiv. Tests patch this to raise; nothing else may import requests."""
    import requests
    return requests.get(url, params=params, headers=headers, timeout=timeout)


def _stamp(date_iso: str, end: bool) -> str:
    y, m, d = date_iso.split("-")
    return f"{y}{m}{d}{'2359' if end else '0000'}"


def build_arxiv_query(question: str, q: Mapping) -> str:
    """Prose -> an arXiv `search_query`: the first `max_terms` non-stopword tokens joined by `operator`, plus an
    optional submittedDate range. Raises ProviderResponseError-free ValueError when no term survives."""
    seen, terms = set(), []
    for tok in re.findall(r"[A-Za-z][A-Za-z0-9\-]*", question.lower()):
        if len(tok) < q["min_term_chars"] or tok in QUERY_STOPWORDS or tok in seen:
            continue
        seen.add(tok)
        terms.append(tok)
        if len(terms) >= q["max_terms"]:
            break
    if not terms:
        raise ValueError("question has no searchable term after stopword removal")
    body = "(" + f" {q['operator']} ".join(f"all:{t}" for t in terms) + ")"
    if q.get("submitted_from") and q.get("submitted_to"):
        body += f" AND submittedDate:[{_stamp(q['submitted_from'], False)} TO {_stamp(q['submitted_to'], True)}]"
    return body


class ArxivProvider:
    """arXiv Atom API, abstract pages only. `settings` is config search.arxiv (validated by eval_config)."""
    name = "arxiv"
    required_env: tuple[str, ...] = ()

    def __init__(self, settings: Mapping, *, transport: Callable | None = None):
        self.s = settings
        self.endpoint = settings["endpoint"]
        self.max_bytes = int(settings["max_response_bytes"])
        self.gate = RateGate(float(settings["min_interval_s"]))
        self._transport = transport

    def call(self, query: str, n: int, timeout_s: float):
        params = {"search_query": build_arxiv_query(query, self.s["query"]), "start": 0, "max_results": n,
                  "sortBy": "relevance", "sortOrder": "descending"}
        # Resolved at call time so a test patching arxiv_default_transport is honoured.
        tx = self._transport or arxiv_default_transport
        return tx(self.endpoint, params, {"User-Agent": USER_AGENT}, timeout_s)

    def parse(self, resp, n: int) -> list[dict]:
        body = resp.text or ""
        if len(body.encode("utf-8", "ignore")) > self.max_bytes:
            raise ProviderResponseError(f"arxiv response over {self.max_bytes} bytes; refused before parsing")
        low = body.lower()
        if "<!doctype" in low or "<!entity" in low:
            raise ProviderResponseError("arxiv response carries a DOCTYPE/ENTITY declaration; refused (XML bomb guard)")
        try:
            root = ET.fromstring(body)
        except ET.ParseError as e:
            raise ProviderResponseError(f"arxiv response is not well-formed XML: {e}") from None
        if root.tag != ATOM + "feed":
            raise ProviderResponseError(f"arxiv response root is {root.tag!r}, expected an Atom feed")
        out = []
        for entry in root.findall(ATOM + "entry"):
            eid = (entry.findtext(ATOM + "id") or "").strip()
            if "/api/errors" in eid:  # arXiv reports errors as a one-entry feed: a FAILURE, not "no results"
                raise ProviderResponseError("arxiv returned an error entry: "
                                            + " ".join((entry.findtext(ATOM + "summary") or "").split())[:200])
            sp = urlsplit(eid)
            if sp.netloc.lower() not in (ARXIV_HOST, "www." + ARXIV_HOST) or not sp.path.startswith(ARXIV_ABSTRACT_PATH_PREFIX):
                continue  # not an abstract page: never emitted (R1: abstract page only)
            doi = (entry.findtext(ARXIV_NS + "doi") or "").strip() or None
            out.append({
                "url": f"https://{ARXIV_HOST}{sp.path}",
                "title": " ".join((entry.findtext(ATOM + "title") or "").split()),
                "snippet": " ".join((entry.findtext(ATOM + "summary") or "").split()),
                "doi": doi,
                "published": (entry.findtext(ATOM + "published") or "").strip() or None,
                "licence": licence_record(metadata=ARXIV_METADATA_LICENCE),
                # Why: what fetch stores for this URL is the abstract page, i.e. metadata (title, abstract).
                "stored_text_kind": "abstract_metadata",
                "provider_endpoint": self.endpoint,
            })
            if len(out) >= n:
                break
        return out

    def cost_for(self, resp):
        return 0.0, True, COST_BASIS_KEYLESS

    def failure_basis(self) -> str:
        return COST_BASIS_KEYLESS


# ----------------------------------------------------------------------------------------- seed file
def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class _Resp:
    def __init__(self, payload):
        self.status_code, self.payload, self.headers, self.text = 200, payload, {}, ""


def validate_seed(doc, query: str) -> list[dict]:
    """Return the validated items or raise SearchConfigError listing EVERY problem."""
    problems = []
    if not isinstance(doc, dict) or doc.get("schema") != SEED_SCHEMA:
        raise SearchConfigError(f"seed file: schema must be {SEED_SCHEMA!r}")
    strat = doc.get("search_strategy")
    if not isinstance(strat, dict) or not all(strat.get(k) for k in ("queries", "tools", "found_at", "inclusion_rule", "agent", "model")):
        problems.append("search_strategy needs non-empty queries, tools, found_at, inclusion_rule, agent, model")
    elif not doc.get("query_agnostic") and query not in strat["queries"]:
        problems.append("the run query is not among search_strategy.queries and the seed is not declared "
                        "query_agnostic: a seed for a different query is a different run input")
    items = doc.get("items")
    if not isinstance(items, list) or not items:
        problems.append("items: missing or empty")
        items = []
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            problems.append(f"items[{i}]: not an object")
            continue
        for k in SEED_ITEM_REQUIRED:
            if not it.get(k):
                problems.append(f"items[{i}].{k}: missing or empty")
        lic = it.get("licence")
        if lic is not None and not (isinstance(lic, dict) and set(lic) <= {"metadata", "content"}):
            problems.append(f"items[{i}].licence: must be an object with optional metadata/content records")
    if problems:
        raise SearchConfigError("seed file invalid: " + "; ".join(problems[:20]))
    return items


class SeedFileProvider:
    """DISCLOSED FALLBACK: reads an agent-prepared candidate list, verifies its sha256 first."""
    required_env: tuple[str, ...] = ()
    endpoint = "file"

    def __init__(self, path: Path, expected_sha256: str):
        self.path, self.expected = Path(path), expected_sha256
        self.name = f"seed:{expected_sha256[:8]}"
        self.gate = RateGate(0.0)

    def call(self, query: str, n: int, timeout_s: float):
        try:
            data = self.path.read_bytes()
        except OSError as e:
            raise SearchConfigError(f"seed file {self.path} unreadable: {type(e).__name__}: {e}") from None
        got = hashlib.sha256(data).hexdigest()
        if got != self.expected:
            raise SearchConfigError(f"seed file sha256 {got[:16]}... != frozen {self.expected[:16]}...: a changed "
                                    "seed file is a different run input (re-freeze it in the run config)")
        try:
            doc = json.loads(data)
        except ValueError as e:
            raise SearchConfigError(f"seed file is not valid JSON: {e}") from None
        validate_seed(doc, query)
        return _Resp({"doc": doc, "sha256": got})

    def parse(self, resp, n: int) -> list[dict]:
        out = []
        for it in resp.payload["doc"]["items"]:
            lic = it.get("licence") or {}
            out.append({"url": it["url"], "title": it["title"], "snippet": it["snippet"], "doi": it.get("doi"),
                        "published": it.get("published"),
                        "licence": licence_record(lic.get("metadata"), lic.get("content")),
                        "stored_text_kind": "full_content", "provider_endpoint": "file:" + self.expected,
                        "reliability_tier": it["reliability_tier"], "found_by": it["found_by"]})
        return out

    def cost_for(self, resp):
        return 0.0, True, COST_BASIS_SEED

    def failure_basis(self) -> str:
        return COST_BASIS_SEED


# ----------------------------------------------------------------------------------------- registry
PROVIDER_FACTORIES: dict[str, Callable] = {
    "arxiv": lambda settings, **kw: ArxivProvider(settings["arxiv"], **kw),
}
# Why: names the extension seam only; there is deliberately no factory for a spending provider (R1 D5).
KNOWN_PROVIDER_NAMES = tuple(PROVIDER_FACTORIES)


def build_chain(settings: Mapping, *, repo_root: Path, transport: Callable | None = None) -> list:
    """Providers in route order from config `search`; the seed fallback (when configured) is LAST."""
    chain = []
    for name in settings["providers"]:
        factory = PROVIDER_FACTORIES.get(name)
        if factory is None:
            raise SearchConfigError(f"unknown search provider {name!r}; known: {list(KNOWN_PROVIDER_NAMES)}")
        chain.append(factory(settings, **({"transport": transport} if transport else {})))
    fb = settings.get("fallback_seed") or {}
    if fb.get("path") or fb.get("sha256"):
        if not (fb.get("path") and fb.get("sha256")):
            raise SearchConfigError("search.fallback_seed needs BOTH path and sha256 (frozen by hash)")
        chain.append(SeedFileProvider(Path(repo_root) / fb["path"], fb["sha256"]))
    return chain
