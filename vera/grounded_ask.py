"""Item #79: grounded /ask. Live scholarly retrieval once per accepted question, the measured grounded-v1
prompt, and a citation check on the answer.

Settings come from the `grounding` block of config/ask-provider-chain.json. Retrieval uses VERA's own
keyless search providers; results with an abstract are used directly and link-only results are followed to
their original sources (vera/source_resolver.py), so every numbered source gives the model text to ground
on. Nothing is stored: no database, no corpus file.
"""
import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Callable

from vera.trace_eval.capture import grounded_v1_messages

logger = logging.getLogger("vera")

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "ask-provider-chain.json"
_CITE_GROUP = re.compile(r"\[(\s*\d+\s*(?:[,;–-]\s*\d+\s*)*)\]")


def load_grounding(path: Path = CONFIG_PATH) -> dict | None:
    """The grounding block, or None when it is missing, unreadable or disabled (then /ask is ungrounded)."""
    try:
        g = json.loads(Path(path).read_text()).get("grounding") or {}
    except (OSError, ValueError):
        return None
    return g if g.get("enabled") else None


def load_corpus_cfg(path: Path = CONFIG_PATH) -> dict | None:
    """The corpus block (phase C), or None when missing, unreadable or disabled."""
    try:
        c = json.loads(Path(path).read_text()).get("corpus") or {}
    except (OSError, ValueError):
        return None
    return c if c.get("enabled") else None


def clean_text(text: str, max_chars: int) -> str:
    """Drop invisible/format Unicode (prompt-injection hiding place) and cap length."""
    s = "".join(ch for ch in str(text or "") if unicodedata.category(ch) != "Cf")
    s = re.sub(r"\s+", " ", s).strip()
    return s[:max_chars]


def _provider_chain(names: list[str]):
    from vera.search_and_fetch import _search_settings, cached_chain

    chain, _, _ = cached_chain(_search_settings())  # cached per process: provider rate gates persist
    return [p for p in chain if p.name in set(names)]


def retrieve(question: str, cfg: dict, search: Callable | None = None, resolver: Callable | None = None) -> list[dict]:
    """Numbered sources with abstracts (the prompt's sources)."""
    return retrieve_all(question, cfg, search, resolver)[0]


def retrieve_all(question: str, cfg: dict, search: Callable | None = None,
                 resolver: Callable | None = None) -> tuple[list[dict], list[dict]]:
    """(sources, unused): numbered sources with abstracts [{n, title, url, published, snippet, source_type}],
    and original sources that were traced but have no free abstract (listed, never used). ([], []) on failure."""
    try:
        if search is None:
            from vera.search_and_fetch import search_question

            providers = _provider_chain(cfg["providers"])
            # per-provider timeout below the overall deadline, so one slow provider cannot starve the others
            results = search_question(question, num_results=int(cfg["num_results"]), providers=providers,
                                      min_candidates=1, mode="fan_out", deadline_s=float(cfg["deadline_s"]),
                                      timeout_s=float(cfg.get("provider_timeout_s", 5)),
                                      max_retries=int(cfg.get("provider_max_retries", 1)))
        else:
            results = search(question)
    except Exception as exc:  # noqa: BLE001  (search failure -> no-sources message, logged by class only)
        logger.warning("/ask grounding search failed (%s)", type(exc).__name__)
        return [], []
    direct = [r for r in results if clean_text(r.get("snippet"), 1)]
    linked = [r for r in results if not clean_text(r.get("snippet"), 1)]
    if len(direct) >= int(cfg["num_results"]):
        linked = []  # enough sources with abstracts already; skip the slower link following
    rcfg = cfg.get("resolve") or {}
    if linked and rcfg.get("enabled"):
        direct += _resolve_links(linked, rcfg, resolver)
    out, seen, unused = [], set(), []
    for r in direct:
        snippet = clean_text(r.get("snippet"), int(cfg["snippet_max_chars"]))
        url = str(r.get("url") or "")
        key = str(r.get("doi") or "").lower() or url.lower().rstrip("/")
        if not url.lower().startswith(("https://", "http://")) or key in seen:
            continue
        if not snippet:
            if r.get("discovered_via"):  # a traced original without a free abstract: show it, never ground on it
                seen.add(key)
                unused.append({"title": clean_text(r.get("title"), 300) or url, "url": url,
                               "published": (str(r.get("published"))[:10] if r.get("published") else None),
                               "discovered_via": str(r["discovered_via"])})
            continue
        seen.add(key)
        src = {"n": len(out) + 1, "title": clean_text(r.get("title"), 300) or url, "url": url,
               "published": (str(r.get("published"))[:10] if r.get("published") else None),
               "snippet": snippet, "source_type": r.get("source_type")}
        if r.get("discovered_via"):
            src["discovered_via"] = str(r["discovered_via"])
        for k in ("licence", "stored_text_kind", "doi"):  # internal, for the corpus gauntlet; never in the response
            if r.get(k):
                src[k] = r[k]
        src.update(provenance(r))
        out.append(src)
        if len(out) >= int(cfg["num_results"]):
            break
    return out, unused[: int(cfg["num_results"])]


def _resolve_links(linked: list[dict], rcfg: dict, resolver=None) -> list[dict]:
    """Follow up to max_results_to_resolve link-only results within one deadline; log what was skipped."""
    import time

    from vera.source_resolver import resolve

    resolver = resolver or resolve
    deadline_at = time.monotonic() + float(rcfg["deadline_s"])
    found, tried = [], 0
    for r in linked[: int(rcfg["max_results_to_resolve"])]:
        if time.monotonic() >= deadline_at:
            break
        tried += 1
        try:
            found += resolver(r, rcfg, deadline_at)
        except Exception as exc:  # noqa: BLE001  (one bad page never fails the request)
            logger.warning("/ask link resolution failed (%s)", type(exc).__name__)
    skipped = len(linked) - tried
    if skipped:
        logger.info("/ask link resolution: %d followed, %d skipped (limit or deadline), %d originals found",
                    tried, skipped, len(found))
    return found


_ARXIV_ID = re.compile(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)", re.I)


def provenance(r: dict) -> dict:
    """Per-citation provenance (R1 criterion): provider, identifier, retrieval time, licence decision."""
    from datetime import datetime, timezone

    from vera.licence_gate import licence_decision

    url = str(r.get("url") or "")
    m = _ARXIV_ID.search(url)
    ident = (f"doi:{str(r['doi']).lower()}" if r.get("doi") else f"arXiv:{m.group(1)}" if m else url)
    provider = r.get("provider") or ("openalex" if r.get("discovered_via") else None)
    if r.get("abstract_source"):
        provider = f"{provider or 'openalex'}+{r['abstract_source']}"
    decision, _why = licence_decision({"url": url, "licence": r.get("licence"),
                                       "stored_text_kind": r.get("stored_text_kind")})
    return {"provider": provider or "unknown", "identifier": ident,
            "retrieved_at": r.get("retrieved_at") or datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "licence_decision": decision}


def messages_for(question: str, sources: list[dict]) -> list[dict]:
    return grounded_v1_messages(question, sources)


def _expand(group: str) -> list[int]:
    nums = []
    for part in re.split(r"[,;]", group):
        bounds = [int(x) for x in re.findall(r"\d+", part)]
        if len(bounds) == 2 and bounds[0] <= bounds[1] and bounds[1] - bounds[0] < 50:
            nums.extend(range(bounds[0], bounds[1] + 1))
        else:
            nums.extend(bounds)
    return nums


def fix_citations(answer: str, n_sources: int, note: str) -> tuple[str, int]:
    """Remove citation numbers outside 1..n_sources; return (text, number removed). A note is appended if any."""
    removed = 0

    def repl(m):
        nonlocal removed
        nums = _expand(m.group(1))
        keep = [n for n in nums if 1 <= n <= n_sources]
        removed += len(nums) - len(keep)
        return f"[{', '.join(str(n) for n in dict.fromkeys(keep))}]" if keep else ""

    text = _CITE_GROUP.sub(repl, answer or "")
    if removed:
        text = text.rstrip() + "\n\n" + note
    return text, removed


PUBLIC_FIELDS = ("n", "title", "url", "published", "source_type", "provider", "identifier", "retrieved_at",
                 "licence_decision")


def public_sources(sources: list[dict]) -> list[dict]:
    """What the response shows: no abstracts (short-quote rule); id, title, link, date, type and provenance."""
    return [{k: s.get(k) for k in PUBLIC_FIELDS} for s in sources]


def count_valid_citations(answer: str, n_sources: int) -> int:
    return sum(1 for g in _CITE_GROUP.findall(answer or "") for n in _expand(g) if 1 <= n <= n_sources)
