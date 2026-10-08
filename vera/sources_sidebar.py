"""Item #78: sidebar expander telling visitors what VERA's answers draw on.

Everything shown is read from files shipped with the app (scope router config, /ask provider chain config,
the Trace Eval results snapshot); no database, API, environment variable or host is read or shown.
"""
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCOPE_PATH = ROOT / "config" / "scope_router.json"
CHAIN_PATH = ROOT / "config" / "ask-provider-chain.json"
SELECTION_PATH = ROOT / "config" / "model-selection.json"
SNAPSHOT_PATH = ROOT / "eval_results" / "trace_eval_v1.json"
SAMPLE_SIZE = 5
_ARXIV_ID = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{2})(\d{2})\.\d{4,5}")
_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~])")


def _read(path: Path) -> dict | None:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def plain(text: str) -> str:
    """Escape Markdown so a source title renders as literal text."""
    return _MD_SPECIAL.sub(r"\\\1", str(text))


def scope_text(path: Path = SCOPE_PATH) -> str | None:
    cfg = _read(path)
    return str(cfg["scope"]) if cfg and cfg.get("scope") else None


def answer_providers(chain_path: Path = CHAIN_PATH, selection_path: Path = SELECTION_PATH) -> list[str]:
    """Provider:model names in the order /ask tries them (names only, no keys or endpoints)."""
    chain = _read(chain_path) or {}
    names = [f"{p['provider']} {p['model']}" for p in chain.get("providers", []) if p.get("provider") and p.get("model")]
    sel = _read(selection_path) or {}
    if sel.get("selected_model"):
        names.append(f"openai {sel['selected_model']}")
    return names


def snapshot_summary(path: Path = SNAPSHOT_PATH) -> dict | None:
    """Distinct sources retrieved for the Trace Eval snapshot, the year span of their arXiv ids, and titles."""
    res = _read(path)
    if not res:
        return None
    sources = {}
    for t in res.get("traces", []):
        for s in t.get("sources") or []:
            if s.get("url"):
                sources[s["url"]] = s.get("title") or s["url"]
    years = sorted({2000 + int(m.group(1)) for u in sources if (m := _ARXIV_ID.search(u))})
    questions = len({t.get("id") for t in res.get("traces", []) if t.get("id")})
    return {"count": len(sources), "years": (years[0], years[-1]) if years else None,
            "questions": questions, "captured": str(res.get("generated_at") or "")[:10] or None,
            "titles": list(sources.values())}


CORPUS_REFRESH_S = 600  # per browser session: how often the sidebar re-asks the API (the API caches anyway)


def _corpus(st) -> dict | None:
    """Item #83: the API's corpus description, fetched server-side and kept for CORPUS_REFRESH_S per session."""
    import os
    import time

    from vera.public_mode import get_corpus_summary, upstream_base_url
    cached = st.session_state.get("_vera_corpus")
    if cached and time.monotonic() - cached[0] < CORPUS_REFRESH_S:
        return cached[1]
    data = get_corpus_summary(upstream_base_url(), os.getenv("VERA_API_KEY", ""))
    st.session_state["_vera_corpus"] = (time.monotonic(), data)
    return data


def render_corpus(st, data: dict | None) -> None:
    if not data or data.get("summary_source") in (None, "disabled", "unavailable", "not_connected"):
        st.caption("**VERA's corpus:** description not available right now.")
        return
    when = f", newest source {plain(data['corpus_updated_at'][:10])}" if data.get("corpus_updated_at") else ""
    st.caption(f"**VERA's corpus:** {int(data.get('source_count') or 0)} sources admitted by Gate A and the "
               f"licence gate{when}.")
    if data.get("summary"):
        st.caption(plain(data["summary"]))
    if data.get("topics"):
        st.caption("Topics: " + plain(", ".join(data["topics"])))
    if data.get("summary_source") == "agentic_model":
        st.caption(f"Description written by {plain(data.get('summary_model') or 'a model')} on "
                   f"{plain((data.get('summary_generated_at') or '')[:10])}; refreshed when the corpus changes.")


def render_sources_sidebar(st, rng: random.Random | None = None) -> None:
    with st.sidebar.expander("📚 What VERA draws on", expanded=False):
        render_corpus(st, _corpus(st))
        scope = scope_text()
        st.caption(f"**Scope:** {plain(scope)}" if scope else "**Scope:** not available")
        providers = answer_providers()
        st.caption("**How VERA answers (retrieval-augmented generation):** for each in-scope question the Ask page "
                   "searches published sources live (arXiv, OpenAlex, and web results followed back to the original "
                   "papers), answers only from the abstracts it found, cites them as [n] and lists them under the "
                   "answer. If no usable source is found it says so instead of answering from memory. Abstracts can "
                   "omit methods and limits, so open the sources before relying on a claim."
                   + (f" Models, in the order tried: {plain(', '.join(providers))}." if providers else ""))
        snap = snapshot_summary()
        if not snap or not snap["count"]:
            st.caption("**Evidence snapshot:** not available")
            return
        span = f", arXiv identifiers from {snap['years'][0]} to {snap['years'][1]}" if snap["years"] else ""
        when = f", captured {snap['captured']} (UTC; replaced when the evaluation is re-run)" if snap["captured"] else ""
        st.caption(f"**Evidence snapshot (Trace Eval page):** {snap['count']} distinct arXiv abstracts retrieved "
                   f"for {snap['questions']} test questions{span}{when}. A random sample of titles:")
        titles = snap["titles"]
        for title in (rng or random).sample(titles, min(SAMPLE_SIZE, len(titles))):
            st.caption(f"• {plain(title)}")


def _link(title: str, url: str) -> str:
    safe_url = str(url or "")
    if not safe_url.lower().startswith(("https://", "http://")) or any(c in safe_url for c in " ()<>\"'"):
        return plain(title)
    return f"[{plain(title)}]({safe_url})"


def render_sources(st, sources: list[dict], traced: list[dict], claim_check: dict | None = None) -> None:
    """Sources under an Ask answer: numbered (used) and traced originals without a free abstract (not used)."""
    if sources:
        st.markdown("**Sources** (abstracts the answer was grounded in)")
        for s in sources:
            date = f" ({plain(s['published'])})" if s.get("published") else ""
            st.markdown(f"[{int(s['n'])}] {_link(s.get('title') or s.get('url'), s.get('url'))}{date}")
            meta = " · ".join(plain(str(s[k])) for k in ("identifier", "provider", "retrieved_at", "licence_decision")
                              if s.get(k))
            if meta:
                st.caption(meta)
    if claim_check and claim_check.get("outcome") == "checked":
        st.caption(f"Claim check ({plain(claim_check.get('checker') or 'checker')}): {claim_check['checked']} cited "
                   f"claims checked against the cited abstracts; {claim_check['supported']} supported, "
                   f"{claim_check['partial']} partly supported, {claim_check['removed']} removed.")
    if traced:
        st.caption("Also traced from web results to the original source, but no free abstract was available, so "
                   "not used: " + "; ".join(_link(t.get("title") or t.get("url"), t.get("url")) for t in traced))
