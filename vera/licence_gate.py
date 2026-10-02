"""Licence gate (R1 #63, scope S-ab): decides, per candidate, whether its text may be stored.

Rules: a declared NC or ND licence is rejected; no declared licence is deferred for review; anything else
is allowed. The GOVERNING licence depends on what fetch will store:
  * stored_text_kind == "abstract_metadata" (the arXiv abstract page): the METADATA licence governs (CC0);
  * anything else (full content): the CONTENT licence governs. A metadata licence (e.g. CC0 on an abstract)
    is NEVER permission to store content.
An NC/ND id on either record rejects. arXiv e-print URLs (pdf, html, e-print) are rejected outright (terms).
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

# Why: arXiv's terms forbid storing/serving e-prints without permission; only /abs/ pages may be stored.
ARXIV_HOSTS = ("arxiv.org", "www.arxiv.org", "export.arxiv.org")
ARXIV_ALLOWED_PREFIX = "/abs/"
METADATA_KIND = "abstract_metadata"


def is_nc_or_nd(licence_id: str | None, licence_url: str | None = None) -> bool:
    """True when an id or URL names a NonCommercial or NoDerivatives term (token match: BY-NC-4.0, by-nd)."""
    text = f"{licence_id or ''} {licence_url or ''}".upper()
    return bool({"NC", "ND"} & set(re.split(r"[^A-Z0-9]+", text)))


def licence_decision(c: dict) -> tuple[str, str]:
    sp = urlsplit(c.get("url", ""))
    if sp.netloc.lower() in ARXIV_HOSTS and not sp.path.startswith(ARXIV_ALLOWED_PREFIX):
        return "reject", "arXiv e-print/PDF/HTML is never stored (arXiv terms); only the abstract page"
    lic = c.get("licence") or {}
    meta, content = lic.get("metadata") or {}, lic.get("content") or {}
    for rec in (meta, content):
        if rec.get("id") and is_nc_or_nd(rec.get("id"), rec.get("url")):
            return "reject", f"licence {rec['id']} is NC/ND (#63)"
    governing = meta if c.get("stored_text_kind") == METADATA_KIND else content
    if not governing.get("id"):
        return "defer", "no declared licence for the stored text: held for review (#63)"
    return "allow", f"licence {governing['id']}"


def apply_licence_gate(scored: list[dict]) -> list[dict]:
    """Mutates and returns `scored`. A Gate A reject is kept; otherwise reject/defer override a fetch."""
    for c in scored:
        d, why = licence_decision(c)
        c["licence_decision"] = d
        if d != "allow" and c.get("gate_a_decision") != "reject":
            c["gate_a_decision"] = d
        c["gate_a_rationale"] = f"{c.get('gate_a_rationale', '')} Licence: {why}."
    return scored
